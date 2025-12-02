//go:build windows

package collector

import (
	"encoding/xml"
	"fmt"
	"log"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"

	"siem-agent/internal/config"
	"siem-agent/internal/sysinfo"
)

var (
	wevtapi                    = windows.NewLazySystemDLL("wevtapi.dll")
	procEvtSubscribe           = wevtapi.NewProc("EvtSubscribe")
	procEvtRender              = wevtapi.NewProc("EvtRender")
	procEvtClose               = wevtapi.NewProc("EvtClose")
	procEvtNext                = wevtapi.NewProc("EvtNext")
	procEvtCreateRenderContext = wevtapi.NewProc("EvtCreateRenderContext")
)

const (
	EvtSubscribeToFutureEvents = 1
	EvtRenderEventXml          = 1
	EvtRenderEventValues       = 0
)

// EventLogCollector collects events from Windows Event Log
type EventLogCollector struct {
	config     *config.Config
	sysInfo    *sysinfo.SystemInfo
	agentID    string
	channels   []string
	eventQueue chan *Event
	wg         sync.WaitGroup
	stopChan   chan struct{}
	mu         sync.Mutex
}

// XMLEvent represents parsed Windows Event XML
type XMLEvent struct {
	XMLName xml.Name `xml:"Event"`
	System  struct {
		Provider struct {
			Name string `xml:"Name,attr"`
		} `xml:"Provider"`
		EventID     int    `xml:"EventID"`
		Version     int    `xml:"Version"`
		Level       int    `xml:"Level"`
		Task        int    `xml:"Task"`
		Opcode      int    `xml:"Opcode"`
		Keywords    string `xml:"Keywords"`
		TimeCreated struct {
			SystemTime string `xml:"SystemTime,attr"`
		} `xml:"TimeCreated"`
		EventRecordID int64  `xml:"EventRecordID"`
		Correlation   string `xml:"Correlation"`
		Execution     struct {
			ProcessID int `xml:"ProcessID,attr"`
			ThreadID  int `xml:"ThreadID,attr"`
		} `xml:"Execution"`
		Channel  string `xml:"Channel"`
		Computer string `xml:"Computer"`
		Security struct {
			UserID string `xml:"UserID,attr"`
		} `xml:"Security"`
	} `xml:"System"`
	EventData struct {
		Data []struct {
			Name  string `xml:"Name,attr"`
			Value string `xml:",chardata"`
		} `xml:"Data"`
	} `xml:"EventData"`
	UserData struct {
		Data []struct {
			Name  string `xml:"Name,attr"`
			Value string `xml:",chardata"`
		} `xml:",any"`
	} `xml:"UserData"`
}

// NewEventLogCollector creates a new Event Log collector
func NewEventLogCollector(cfg *config.Config, agentID string, eventQueue chan *Event) (*EventLogCollector, error) {
	sysInfo, err := sysinfo.Gather()
	if err != nil {
		return nil, fmt.Errorf("failed to gather system info: %w", err)
	}

	channels := cfg.EventLog.GetEnabledChannels()
	if len(channels) == 0 {
		return nil, fmt.Errorf("no event log channels enabled")
	}

	return &EventLogCollector{
		config:     cfg,
		sysInfo:    sysInfo,
		agentID:    agentID,
		channels:   channels,
		eventQueue: eventQueue,
		stopChan:   make(chan struct{}),
	}, nil
}

// Start begins collecting events from all enabled channels
func (c *EventLogCollector) Start() error {
	log.Printf("Starting Event Log collector for %d channels", len(c.channels))

	for _, channel := range c.channels {
		c.wg.Add(1)
		go c.collectFromChannel(channel)
	}

	return nil
}

// Stop stops the collector
func (c *EventLogCollector) Stop() {
	close(c.stopChan)
	c.wg.Wait()
	log.Println("Event Log collector stopped")
}

// collectFromChannel collects events from a specific channel
func (c *EventLogCollector) collectFromChannel(channel string) {
	defer c.wg.Done()

	log.Printf("Starting collection from channel: %s", channel)

	// Subscribe to events
	channelPtr, err := syscall.UTF16PtrFromString(channel)
	if err != nil {
		log.Printf("Error converting channel name %s: %v", channel, err)
		return
	}

	var hSubscription uintptr
	ret, _, _ := procEvtSubscribe.Call(
		0,                            // Session
		0,                            // SignalEvent
		uintptr(unsafe.Pointer(channelPtr)),
		0,                            // Query (null = all events)
		0,                            // Bookmark
		0,                            // Context
		0,                            // Callback
		EvtSubscribeToFutureEvents,   // Flags
	)

	if ret == 0 {
		log.Printf("Failed to subscribe to channel %s", channel)
		return
	}
	defer procEvtClose.Call(ret)
	hSubscription = ret

	// Process events
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-c.stopChan:
			return
		case <-ticker.C:
			c.processEvents(hSubscription, channel)
		}
	}
}

// processEvents processes available events from subscription
func (c *EventLogCollector) processEvents(hSubscription uintptr, channel string) {
	var events [100]uintptr
	var returned uint32

	ret, _, _ := procEvtNext.Call(
		hSubscription,
		uintptr(len(events)),
		uintptr(unsafe.Pointer(&events[0])),
		1000, // timeout ms
		0,
		uintptr(unsafe.Pointer(&returned)),
	)

	if ret == 0 || returned == 0 {
		return
	}

	for i := uint32(0); i < returned; i++ {
		if events[i] != 0 {
			c.processEvent(events[i], channel)
			procEvtClose.Call(events[i])
		}
	}
}

// processEvent processes a single event
func (c *EventLogCollector) processEvent(hEvent uintptr, channel string) {
	// Render event as XML
	xmlData := c.renderEventAsXML(hEvent)
	if xmlData == "" {
		return
	}

	// Parse XML
	var xmlEvent XMLEvent
	if err := xml.Unmarshal([]byte(xmlData), &xmlEvent); err != nil {
		log.Printf("Failed to parse event XML: %v", err)
		return
	}

	// Check if event should be excluded
	if c.config.EventLog.IsEventIDExcluded(xmlEvent.System.EventID) {
		return
	}

	// Parse event time
	eventTime, _ := time.Parse(time.RFC3339Nano, xmlEvent.System.TimeCreated.SystemTime)

	// Create normalized event
	event := &Event{
		AgentID:     c.agentID,
		Computer:    c.sysInfo.Hostname,
		FQDN:        c.sysInfo.FQDN,
		IPAddress:   c.sysInfo.IPAddress,
		SourceType:  c.getSourceType(channel, xmlEvent.System.Provider.Name),
		EventCode:   xmlEvent.System.EventID,
		EventTime:   eventTime,
		RecordID:    xmlEvent.System.EventRecordID,
		Channel:     channel,
		Provider:    xmlEvent.System.Provider.Name,
		Severity:    SeverityFromWindowsLevel(xmlEvent.System.Level),
		RawXML:      xmlData,
		CollectedAt: time.Now(),
	}

	// Extract event data fields
	c.extractEventData(event, &xmlEvent)

	// Send to queue
	select {
	case c.eventQueue <- event:
	case <-c.stopChan:
		return
	default:
		log.Printf("Warning: Event queue full, dropping event %d", event.EventCode)
	}
}

// renderEventAsXML renders event handle as XML string
func (c *EventLogCollector) renderEventAsXML(hEvent uintptr) string {
	var bufferUsed, propertyCount uint32
	var buffer [65536]byte

	ret, _, _ := procEvtRender.Call(
		0, // Context
		hEvent,
		EvtRenderEventXml,
		uintptr(len(buffer)),
		uintptr(unsafe.Pointer(&buffer[0])),
		uintptr(unsafe.Pointer(&bufferUsed)),
		uintptr(unsafe.Pointer(&propertyCount)),
	)

	if ret == 0 {
		return ""
	}

	// Convert UTF-16 to string
	return windows.UTF16ToString((*[32768]uint16)(unsafe.Pointer(&buffer[0]))[:bufferUsed/2])
}

// getSourceType determines source type based on channel and provider
func (c *EventLogCollector) getSourceType(channel, provider string) string {
	if strings.Contains(channel, "Security") {
		return "Windows Security"
	}
	if strings.Contains(channel, "Sysmon") || strings.Contains(provider, "Sysmon") {
		return "Sysmon"
	}
	if strings.Contains(channel, "PowerShell") {
		return "PowerShell"
	}
	if strings.Contains(channel, "System") {
		return "Windows System"
	}
	if strings.Contains(channel, "Application") {
		return "Windows Application"
	}
	return "Windows Event"
}

// extractEventData extracts relevant fields from event data
func (c *EventLogCollector) extractEventData(event *Event, xmlEvent *XMLEvent) {
	eventData := make(map[string]string)

	// Extract from EventData
	for _, data := range xmlEvent.EventData.Data {
		if data.Name != "" {
			eventData[data.Name] = data.Value
		}
	}

	// Extract from UserData
	for _, data := range xmlEvent.UserData.Data {
		if data.Name != "" {
			eventData[data.Name] = data.Value
		}
	}

	// Process ID from System
	if xmlEvent.System.Execution.ProcessID > 0 {
		event.ProcessID = xmlEvent.System.Execution.ProcessID
	}

	// Parse common fields based on event type
	switch event.EventCode {
	case 4624, 4625: // Logon success/failure
		event.SubjectUser = eventData["SubjectUserName"]
		event.SubjectDomain = eventData["SubjectDomainName"]
		event.SubjectLogonID = eventData["SubjectLogonId"]
		event.TargetUser = eventData["TargetUserName"]
		event.TargetDomain = eventData["TargetDomainName"]
		event.TargetLogonID = eventData["TargetLogonId"]
		event.WorkstationName = eventData["WorkstationName"]
		event.SourceIP = eventData["IpAddress"]
		event.AuthPackage = eventData["AuthenticationPackageName"]
		if lt, err := strconv.Atoi(eventData["LogonType"]); err == nil {
			event.LogonType = lt
		}
		if event.EventCode == 4625 {
			event.FailureReason = eventData["FailureReason"]
		}

	case 4688: // Process creation
		event.SubjectUser = eventData["SubjectUserName"]
		event.SubjectDomain = eventData["SubjectDomainName"]
		event.ProcessName = eventData["NewProcessName"]
		event.ProcessCommandLine = eventData["CommandLine"]
		if pid, err := strconv.Atoi(eventData["NewProcessId"]); err == nil {
			event.ProcessID = pid
		}
		if ppid, err := strconv.Atoi(eventData["ProcessId"]); err == nil {
			event.ParentProcessID = ppid
		}

	case 4657, 4663: // Object access
		event.SubjectUser = eventData["SubjectUserName"]
		event.SubjectDomain = eventData["SubjectDomainName"]
		event.ObjectType = eventData["ObjectType"]
		event.FilePath = eventData["ObjectName"]
		event.ProcessName = eventData["ProcessName"]
		event.AccessMask = eventData["AccessMask"]

	case 4697: // Service installed
		event.ServiceName = eventData["ServiceName"]
		event.ServiceAccount = eventData["ServiceAccount"]
		event.ServiceType = eventData["ServiceType"]
		event.ProcessName = eventData["ServiceFileName"]

	case 5140, 5145: // Network share access
		event.SubjectUser = eventData["SubjectUserName"]
		event.SubjectDomain = eventData["SubjectDomainName"]
		event.SourceIP = eventData["IpAddress"]
		event.FilePath = eventData["ShareName"]
		event.AccessMask = eventData["AccessMask"]

	case 1102: // Audit log cleared
		event.SubjectUser = eventData["SubjectUserName"]
		event.SubjectDomain = eventData["SubjectDomainName"]
	}

	// Store remaining data
	event.EventData = eventData

	// Generate message from event data
	event.Message = c.generateMessage(event, eventData)
}

// generateMessage generates a human-readable message from event data
func (c *EventLogCollector) generateMessage(event *Event, eventData map[string]string) string {
	switch event.EventCode {
	case 4624:
		return fmt.Sprintf("Successful logon: %s\\%s from %s (Type: %d)",
			event.TargetDomain, event.TargetUser, event.SourceIP, event.LogonType)
	case 4625:
		return fmt.Sprintf("Failed logon: %s\\%s from %s (Reason: %s)",
			event.TargetDomain, event.TargetUser, event.SourceIP, event.FailureReason)
	case 4688:
		return fmt.Sprintf("Process created: %s (PID: %d, User: %s\\%s)",
			event.ProcessName, event.ProcessID, event.SubjectDomain, event.SubjectUser)
	case 4697:
		return fmt.Sprintf("Service installed: %s (Account: %s)",
			event.ServiceName, event.ServiceAccount)
	case 1102:
		return fmt.Sprintf("Audit log cleared by %s\\%s",
			event.SubjectDomain, event.SubjectUser)
	default:
		// Generic message from provider
		if msg, ok := eventData["Message"]; ok {
			return msg
		}
		return fmt.Sprintf("Event %d from %s", event.EventCode, event.Provider)
	}
}
