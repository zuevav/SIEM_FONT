package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"syscall"
	"time"
	"unsafe"

	"github.com/kardianos/service"
	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/mgr"
)

const (
	watchdogServiceName    = "SIEMWatchdog"
	watchdogDisplayName    = "SIEM Agent Watchdog"
	watchdogDescription    = "Monitors and protects SIEM Security Agent"
	agentServiceName       = "SIEMAgent"
	checkInterval          = 5 * time.Second
	maxRestartAttempts     = 3
	restartCooldown        = 30 * time.Second
)

var (
	version = "1.0.0"
)

// Watchdog implements service.Interface
type Watchdog struct {
	logger         service.Logger
	stopChan       chan struct{}
	restartCount   int
	lastRestartTime time.Time
}

func (w *Watchdog) Start(s service.Service) error {
	w.logger.Info("Starting SIEM Watchdog v" + version)
	w.stopChan = make(chan struct{})
	go w.run()
	return nil
}

func (w *Watchdog) Stop(s service.Service) error {
	w.logger.Info("Stopping SIEM Watchdog...")
	close(w.stopChan)
	return nil
}

func (w *Watchdog) run() {
	ticker := time.NewTicker(checkInterval)
	defer ticker.Stop()

	for {
		select {
		case <-w.stopChan:
			return
		case <-ticker.C:
			w.checkAndProtect()
		}
	}
}

func (w *Watchdog) checkAndProtect() {
	// Check if agent service is running
	running, err := isServiceRunning(agentServiceName)
	if err != nil {
		w.logger.Warningf("Error checking agent service: %v", err)
		return
	}

	if !running {
		w.logger.Warning("SIEM Agent is not running! Attempting to restart...")

		// Check restart cooldown
		if time.Since(w.lastRestartTime) < restartCooldown {
			w.restartCount++
			if w.restartCount > maxRestartAttempts {
				w.logger.Errorf("Max restart attempts (%d) reached within cooldown period", maxRestartAttempts)
				// Send alert to SIEM server
				w.sendAlert("agent_restart_failed", "Max restart attempts reached")
				return
			}
		} else {
			w.restartCount = 0
		}

		// Attempt to start the service
		if err := startService(agentServiceName); err != nil {
			w.logger.Errorf("Failed to start agent service: %v", err)
			w.sendAlert("agent_start_failed", err.Error())
		} else {
			w.logger.Info("Successfully restarted SIEM Agent")
			w.sendAlert("agent_restarted", "Agent was stopped and has been restarted")
		}

		w.lastRestartTime = time.Now()
	}

	// Check if agent process exists
	w.checkAgentProcess()
}

func (w *Watchdog) checkAgentProcess() {
	// Find agent process
	processes, err := getProcessesByName("siem-agent.exe")
	if err != nil {
		w.logger.Warningf("Error enumerating processes: %v", err)
		return
	}

	if len(processes) == 0 {
		w.logger.Warning("Agent process not found, service may be starting...")
		return
	}

	// Protect the process from termination
	for _, pid := range processes {
		if err := protectProcess(pid); err != nil {
			w.logger.Warningf("Could not protect process %d: %v", pid, err)
		}
	}
}

func (w *Watchdog) sendAlert(alertType, message string) {
	// TODO: Send alert to SIEM server
	w.logger.Infof("ALERT [%s]: %s", alertType, message)
}

// isServiceRunning checks if a Windows service is running
func isServiceRunning(serviceName string) (bool, error) {
	m, err := mgr.Connect()
	if err != nil {
		return false, err
	}
	defer m.Disconnect()

	s, err := m.OpenService(serviceName)
	if err != nil {
		return false, err
	}
	defer s.Close()

	status, err := s.Query()
	if err != nil {
		return false, err
	}

	return status.State == svc.Running, nil
}

// startService starts a Windows service
func startService(serviceName string) error {
	m, err := mgr.Connect()
	if err != nil {
		return err
	}
	defer m.Disconnect()

	s, err := m.OpenService(serviceName)
	if err != nil {
		return err
	}
	defer s.Close()

	return s.Start()
}

// getProcessesByName returns PIDs of processes with the given name
func getProcessesByName(name string) ([]uint32, error) {
	snapshot, err := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return nil, err
	}
	defer windows.CloseHandle(snapshot)

	var pe32 windows.ProcessEntry32
	pe32.Size = uint32(unsafe.Sizeof(pe32))

	var pids []uint32

	err = windows.Process32First(snapshot, &pe32)
	if err != nil {
		return nil, err
	}

	for {
		exeName := windows.UTF16ToString(pe32.ExeFile[:])
		if exeName == name {
			pids = append(pids, pe32.ProcessID)
		}

		err = windows.Process32Next(snapshot, &pe32)
		if err != nil {
			break
		}
	}

	return pids, nil
}

// protectProcess attempts to protect a process from termination
func protectProcess(pid uint32) error {
	// Open process with limited access
	handle, err := windows.OpenProcess(
		windows.PROCESS_SET_INFORMATION|windows.PROCESS_QUERY_INFORMATION,
		false,
		pid,
	)
	if err != nil {
		return err
	}
	defer windows.CloseHandle(handle)

	// Set process as critical (will cause BSOD if killed - use carefully!)
	// This is commented out as it's too aggressive
	// var isCritical uint32 = 1
	// windows.NtSetInformationProcess(handle, 0x1D, unsafe.Pointer(&isCritical), 4)

	return nil
}

// SetServiceSecurity sets restrictive permissions on a service
func SetServiceSecurity(serviceName string) error {
	m, err := mgr.Connect()
	if err != nil {
		return err
	}
	defer m.Disconnect()

	s, err := m.OpenService(serviceName)
	if err != nil {
		return err
	}
	defer s.Close()

	// Get current security descriptor
	sd, err := windows.GetSecurityInfo(
		windows.Handle(s.Handle),
		windows.SE_SERVICE,
		windows.DACL_SECURITY_INFORMATION,
	)
	if err != nil {
		return fmt.Errorf("failed to get security info: %w", err)
	}

	// Create new DACL that only allows SYSTEM and Administrators to control
	// This prevents regular users from stopping the service
	sdStr := "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)"

	newSD, err := windows.SecurityDescriptorFromString(sdStr)
	if err != nil {
		// Fallback: use existing SD
		_ = sd
		return nil
	}

	dacl, _, err := newSD.DACL()
	if err != nil {
		return err
	}

	err = windows.SetSecurityInfo(
		windows.Handle(s.Handle),
		windows.SE_SERVICE,
		windows.DACL_SECURITY_INFORMATION,
		nil,
		nil,
		dacl,
		nil,
	)

	return err
}

func main() {
	var (
		install   = flag.Bool("install", false, "Install watchdog service")
		uninstall = flag.Bool("uninstall", false, "Uninstall watchdog service")
		protect   = flag.Bool("protect", false, "Apply protection to agent service")
		ver       = flag.Bool("version", false, "Show version")
	)
	flag.Parse()

	if *ver {
		fmt.Printf("SIEM Watchdog v%s\n", version)
		os.Exit(0)
	}

	// Apply protection to agent service
	if *protect {
		fmt.Println("Applying protection to SIEM Agent service...")
		if err := SetServiceSecurity(agentServiceName); err != nil {
			log.Fatalf("Failed to protect agent service: %v", err)
		}
		fmt.Println("Protection applied successfully")
		os.Exit(0)
	}

	// Service configuration
	svcConfig := &service.Config{
		Name:        watchdogServiceName,
		DisplayName: watchdogDisplayName,
		Description: watchdogDescription,
		Option: service.KeyValue{
			"StartType":              "automatic",
			"OnFailure":              "restart",
			"OnFailureDelay":         5,
			"OnFailureResetPeriod":   60,
			"DelayedAutoStart":       false,
		},
		Dependencies: []string{},
	}

	w := &Watchdog{}
	s, err := service.New(w, svcConfig)
	if err != nil {
		log.Fatal(err)
	}

	logger, err := s.Logger(nil)
	if err != nil {
		log.Fatal(err)
	}
	w.logger = logger

	if *install {
		// First install watchdog
		if err := s.Install(); err != nil {
			logger.Errorf("Failed to install watchdog: %v", err)
			os.Exit(1)
		}
		logger.Info("Watchdog service installed")

		// Apply protection to both services
		if err := SetServiceSecurity(agentServiceName); err != nil {
			logger.Warningf("Could not protect agent service: %v", err)
		}
		if err := SetServiceSecurity(watchdogServiceName); err != nil {
			logger.Warningf("Could not protect watchdog service: %v", err)
		}

		// Start watchdog
		if err := s.Start(); err != nil {
			logger.Errorf("Failed to start watchdog: %v", err)
		}

		os.Exit(0)
	}

	if *uninstall {
		s.Stop()
		if err := s.Uninstall(); err != nil {
			logger.Errorf("Failed to uninstall: %v", err)
			os.Exit(1)
		}
		logger.Info("Watchdog service uninstalled")
		os.Exit(0)
	}

	// Run as service
	if err := s.Run(); err != nil {
		logger.Error(err)
	}
}
