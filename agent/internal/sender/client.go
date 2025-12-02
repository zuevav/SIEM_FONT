package sender

import (
	"bytes"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"siem-agent/internal/collector"
	"siem-agent/internal/config"
)

// APIClient handles communication with SIEM backend
type APIClient struct {
	config     *config.Config
	httpClient *http.Client
	baseURL    string
	apiKey     string
}

// APIResponse represents a generic API response
type APIResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// NewAPIClient creates a new API client
func NewAPIClient(cfg *config.Config) *APIClient {
	// Create HTTP client with timeout
	httpClient := &http.Client{
		Timeout: time.Duration(cfg.SIEM.SendTimeout) * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: cfg.SIEM.InsecureSkipVerify,
			},
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 10,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	return &APIClient{
		config:     cfg,
		httpClient: httpClient,
		baseURL:    cfg.SIEM.ServerURL,
		apiKey:     cfg.SIEM.APIKey,
	}
}

// RegisterAgent registers the agent with SIEM server
func (c *APIClient) RegisterAgent(data *collector.RegistrationData) error {
	url := c.baseURL + "/api/v1/agents/register"

	respData, err := c.doRequest("POST", url, data)
	if err != nil {
		return fmt.Errorf("registration failed: %w", err)
	}

	log.Printf("Agent registered successfully: %s", data.Hostname)

	// Extract AgentId from response if available
	if respMap, ok := respData.(map[string]interface{}); ok {
		if agentID, ok := respMap["agent_id"].(string); ok && agentID != "" {
			log.Printf("Server assigned Agent ID: %s", agentID)
		}
	}

	return nil
}

// SendHeartbeat sends agent heartbeat
func (c *APIClient) SendHeartbeat(data *collector.HeartbeatData) error {
	url := c.baseURL + "/api/v1/agents/heartbeat"

	_, err := c.doRequest("POST", url, data)
	if err != nil {
		return fmt.Errorf("heartbeat failed: %w", err)
	}

	return nil
}

// SendEvents sends a batch of events
func (c *APIClient) SendEvents(events []*collector.Event) error {
	if len(events) == 0 {
		return nil
	}

	url := c.baseURL + "/api/v1/events/batch"

	startTime := time.Now()
	_, err := c.doRequest("POST", url, events)
	if err != nil {
		return fmt.Errorf("failed to send %d events: %w", len(events), err)
	}

	duration := time.Since(startTime)
	log.Printf("Sent %d events in %v", len(events), duration)

	return nil
}

// SendInventory sends inventory data
func (c *APIClient) SendInventory(items []*collector.InventoryItem) error {
	if len(items) == 0 {
		return nil
	}

	url := c.baseURL + "/api/v1/agents/inventory"

	startTime := time.Now()
	_, err := c.doRequest("POST", url, items)
	if err != nil {
		return fmt.Errorf("failed to send %d inventory items: %w", len(items), err)
	}

	duration := time.Since(startTime)
	log.Printf("Sent %d inventory items in %v", len(items), duration)

	return nil
}

// GetConfig retrieves agent configuration from server (future feature)
func (c *APIClient) GetConfig(agentID string) (map[string]interface{}, error) {
	url := c.baseURL + "/api/v1/agents/" + agentID + "/config"

	respData, err := c.doRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to get config: %w", err)
	}

	if configMap, ok := respData.(map[string]interface{}); ok {
		return configMap, nil
	}

	return nil, fmt.Errorf("invalid config response format")
}

// doRequest performs an HTTP request with authentication and error handling
func (c *APIClient) doRequest(method, url string, data interface{}) (interface{}, error) {
	var reqBody io.Reader

	// Prepare request body
	if data != nil {
		jsonData, err := json.Marshal(data)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonData)
	}

	// Create request
	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "SIEM-Agent/1.0")

	// Authentication
	if c.apiKey != "" {
		req.Header.Set("X-API-Key", c.apiKey)
	}

	// Perform request with retry logic
	var resp *http.Response
	maxRetries := c.config.SIEM.RetryAttempts
	retryDelay := time.Duration(c.config.SIEM.RetryDelay) * time.Second

	for attempt := 0; attempt <= maxRetries; attempt++ {
		if attempt > 0 {
			log.Printf("Retry attempt %d/%d after %v", attempt, maxRetries, retryDelay)
			time.Sleep(retryDelay)
			retryDelay *= 2 // Exponential backoff
		}

		resp, err = c.httpClient.Do(req)
		if err == nil {
			break
		}

		if attempt == maxRetries {
			return nil, fmt.Errorf("request failed after %d attempts: %w", maxRetries+1, err)
		}
	}
	defer resp.Body.Close()

	// Read response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	// Check status code
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		// Try to parse error from response
		var apiResp APIResponse
		if err := json.Unmarshal(body, &apiResp); err == nil && apiResp.Error != "" {
			return nil, fmt.Errorf("API error (HTTP %d): %s", resp.StatusCode, apiResp.Error)
		}
		return nil, fmt.Errorf("HTTP error %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var apiResp APIResponse
	if err := json.Unmarshal(body, &apiResp); err != nil {
		// Response might not be in standard format
		var rawData interface{}
		if err := json.Unmarshal(body, &rawData); err == nil {
			return rawData, nil
		}
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	if !apiResp.Success {
		return nil, fmt.Errorf("API error: %s", apiResp.Error)
	}

	return apiResp.Data, nil
}

// Ping checks connectivity to SIEM server
func (c *APIClient) Ping() error {
	url := c.baseURL + "/api/v1/health"

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", "SIEM-Agent/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("cannot connect to SIEM server: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("SIEM server returned HTTP %d", resp.StatusCode)
	}

	return nil
}

// Close closes the HTTP client
func (c *APIClient) Close() {
	c.httpClient.CloseIdleConnections()
}
