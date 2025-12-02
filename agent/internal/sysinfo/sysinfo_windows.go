//go:build windows

package sysinfo

import (
	"fmt"
	"net"
	"os"
	"runtime"
	"strings"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"golang.org/x/sys/windows/registry"
)

// SystemInfo contains system information
type SystemInfo struct {
	Hostname      string
	FQDN          string
	IPAddress     string
	MACAddress    string
	OSVersion     string
	OSBuild       string
	Architecture  string
	Domain        string
	CPUModel      string
	CPUCores      int
	TotalRAM_MB   int
	TotalDisk_GB  int
}

// GetHostname returns the system hostname
func GetHostname() (string, error) {
	hostname, err := os.Hostname()
	if err != nil {
		return "", fmt.Errorf("failed to get hostname: %w", err)
	}
	return hostname, nil
}

// Gather collects system information
func Gather() (*SystemInfo, error) {
	info := &SystemInfo{
		Architecture: runtime.GOARCH,
	}

	// Hostname
	hostname, err := GetHostname()
	if err != nil {
		return nil, err
	}
	info.Hostname = hostname

	// FQDN
	fqdn, err := getFQDN()
	if err == nil {
		info.FQDN = fqdn
	}

	// IP and MAC address
	ip, mac := getNetworkInfo()
	info.IPAddress = ip
	info.MACAddress = mac

	// OS version
	osVersion, osBuild := getOSVersion()
	info.OSVersion = osVersion
	info.OSBuild = osBuild

	// Domain
	domain, err := getDomain()
	if err == nil {
		info.Domain = domain
	}

	// CPU info
	cpuInfo, err := cpu.Info()
	if err == nil && len(cpuInfo) > 0 {
		info.CPUModel = cpuInfo[0].ModelName
		info.CPUCores = int(cpuInfo[0].Cores)
	}

	// Memory
	memInfo, err := mem.VirtualMemory()
	if err == nil {
		info.TotalRAM_MB = int(memInfo.Total / 1024 / 1024)
	}

	// Disk
	diskInfo, err := disk.Usage("C:\\")
	if err == nil {
		info.TotalDisk_GB = int(diskInfo.Total / 1024 / 1024 / 1024)
	}

	return info, nil
}

// getFQDN returns the fully qualified domain name
func getFQDN() (string, error) {
	hostname, err := os.Hostname()
	if err != nil {
		return "", err
	}

	addrs, err := net.LookupHost(hostname)
	if err != nil {
		return hostname, nil
	}

	for _, addr := range addrs {
		if names, err := net.LookupAddr(addr); err == nil && len(names) > 0 {
			return strings.TrimSuffix(names[0], "."), nil
		}
	}

	return hostname, nil
}

// getNetworkInfo returns primary IP and MAC address
func getNetworkInfo() (string, string) {
	interfaces, err := net.Interfaces()
	if err != nil {
		return "", ""
	}

	for _, iface := range interfaces {
		// Skip loopback and down interfaces
		if iface.Flags&net.FlagLoopback != 0 || iface.Flags&net.FlagUp == 0 {
			continue
		}

		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}

		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}

			// Skip loopback and IPv6
			if ip == nil || ip.IsLoopback() || ip.To4() == nil {
				continue
			}

			return ip.String(), iface.HardwareAddr.String()
		}
	}

	return "", ""
}

// getOSVersion returns Windows version and build number
func getOSVersion() (string, string) {
	hostInfo, err := host.Info()
	if err != nil {
		return "Unknown", "Unknown"
	}

	version := fmt.Sprintf("%s %s", hostInfo.Platform, hostInfo.PlatformVersion)
	build := hostInfo.KernelVersion

	// Try to get more detailed version from registry
	k, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows NT\CurrentVersion`, registry.QUERY_VALUE)
	if err == nil {
		defer k.Close()

		if productName, _, err := k.GetStringValue("ProductName"); err == nil {
			version = productName
		}

		if buildNumber, _, err := k.GetStringValue("CurrentBuildNumber"); err == nil {
			build = buildNumber
		}
	}

	return version, build
}

// getDomain returns the Windows domain name
func getDomain() (string, error) {
	k, err := registry.OpenKey(registry.LOCAL_MACHINE, `SYSTEM\CurrentControlSet\Services\Tcpip\Parameters`, registry.QUERY_VALUE)
	if err != nil {
		return "", err
	}
	defer k.Close()

	domain, _, err := k.GetStringValue("Domain")
	if err != nil {
		return "", err
	}

	return domain, nil
}
