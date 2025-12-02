package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/kardianos/service"
	"github.com/siem/agent/internal/agent"
	"github.com/siem/agent/internal/config"
)

const (
	serviceName        = "SIEMAgent"
	serviceDisplayName = "SIEM Security Agent"
	serviceDescription = "Collects security events and sends them to SIEM system"
)

var (
	version = "1.0.0"
	commit  = "dev"
	date    = "unknown"
)

// Program implements service.Interface
type Program struct {
	agent  *agent.Agent
	logger service.Logger
}

func (p *Program) Start(s service.Service) error {
	p.logger.Info("Starting SIEM Agent v" + version)

	// Load configuration
	cfg, err := config.Load("config.yaml")
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	// Create agent
	p.agent, err = agent.New(cfg, version)
	if err != nil {
		return fmt.Errorf("failed to create agent: %w", err)
	}

	// Start agent in goroutine
	go func() {
		if err := p.agent.Start(); err != nil {
			p.logger.Errorf("Agent error: %v", err)
		}
	}()

	p.logger.Info("SIEM Agent started successfully")
	return nil
}

func (p *Program) Stop(s service.Service) error {
	p.logger.Info("Stopping SIEM Agent...")

	if p.agent != nil {
		if err := p.agent.Stop(); err != nil {
			p.logger.Errorf("Error stopping agent: %v", err)
		}
	}

	p.logger.Info("SIEM Agent stopped")
	return nil
}

func main() {
	// Command line flags
	var (
		install   = flag.Bool("install", false, "Install service")
		uninstall = flag.Bool("uninstall", false, "Uninstall service")
		start     = flag.Bool("start", false, "Start service")
		stop      = flag.Bool("stop", false, "Stop service")
		restart   = flag.Bool("restart", false, "Restart service")
		status    = flag.Bool("status", false, "Service status")
		console   = flag.Bool("console", false, "Run in console (for debugging)")
		ver       = flag.Bool("version", false, "Show version")
	)
	flag.Parse()

	// Show version
	if *ver {
		fmt.Printf("SIEM Agent v%s\n", version)
		fmt.Printf("Build: %s (%s)\n", commit, date)
		os.Exit(0)
	}

	// Service configuration
	svcConfig := &service.Config{
		Name:        serviceName,
		DisplayName: serviceDisplayName,
		Description: serviceDescription,
		Arguments:   []string{},
		Option: service.KeyValue{
			"StartType":         "automatic",
			"OnFailure":         "restart",
			"OnFailureDelay":    5,
			"OnFailureResetPeriod": 60,
		},
	}

	prg := &Program{}
	s, err := service.New(prg, svcConfig)
	if err != nil {
		log.Fatal(err)
	}

	// Setup logger
	errs := make(chan error, 5)
	logger, err := s.Logger(errs)
	if err != nil {
		log.Fatal(err)
	}
	prg.logger = logger

	// Handle service commands
	if *install {
		err := s.Install()
		if err != nil {
			logger.Errorf("Failed to install service: %v", err)
			os.Exit(1)
		}
		logger.Info("Service installed successfully")
		os.Exit(0)
	}

	if *uninstall {
		err := s.Uninstall()
		if err != nil {
			logger.Errorf("Failed to uninstall service: %v", err)
			os.Exit(1)
		}
		logger.Info("Service uninstalled successfully")
		os.Exit(0)
	}

	if *start {
		err := s.Start()
		if err != nil {
			logger.Errorf("Failed to start service: %v", err)
			os.Exit(1)
		}
		logger.Info("Service started")
		os.Exit(0)
	}

	if *stop {
		err := s.Stop()
		if err != nil {
			logger.Errorf("Failed to stop service: %v", err)
			os.Exit(1)
		}
		logger.Info("Service stopped")
		os.Exit(0)
	}

	if *restart {
		err := s.Restart()
		if err != nil {
			logger.Errorf("Failed to restart service: %v", err)
			os.Exit(1)
		}
		logger.Info("Service restarted")
		os.Exit(0)
	}

	if *status {
		status, err := s.Status()
		if err != nil {
			logger.Errorf("Failed to get service status: %v", err)
			os.Exit(1)
		}

		switch status {
		case service.StatusRunning:
			fmt.Println("Service is running")
		case service.StatusStopped:
			fmt.Println("Service is stopped")
		default:
			fmt.Println("Service status unknown")
		}
		os.Exit(0)
	}

	// Run in console mode (for debugging)
	if *console {
		fmt.Printf("Starting SIEM Agent v%s in console mode...\n", version)
		fmt.Println("Press Ctrl+C to exit")

		// Load configuration
		cfg, err := config.Load("config.yaml")
		if err != nil {
			log.Fatalf("Failed to load config: %v", err)
		}

		// Override console logging
		cfg.Logging.Console = true

		// Create agent
		ag, err := agent.New(cfg, version)
		if err != nil {
			log.Fatalf("Failed to create agent: %v", err)
		}

		// Handle Ctrl+C
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

		go func() {
			<-sigChan
			fmt.Println("\nStopping agent...")
			if err := ag.Stop(); err != nil {
				log.Printf("Error stopping agent: %v", err)
			}
			os.Exit(0)
		}()

		// Start agent
		if err := ag.Start(); err != nil {
			log.Fatalf("Agent error: %v", err)
		}

		return
	}

	// Run as service
	err = s.Run()
	if err != nil {
		logger.Error(err)
	}
}
