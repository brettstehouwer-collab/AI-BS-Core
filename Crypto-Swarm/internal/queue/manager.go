package queue

// Manager acts as an in-memory message broker between daemons.
type Manager struct {
	TradeQueue             chan map[string]interface{}
	WatcherTrackingQueue   chan map[string]interface{}
	ResearchQueue          chan map[string]interface{}
}

// NewManager creates and initializes a new Queue Manager.
func NewManager() *Manager {
	return &Manager{
		// Buffered channels to prevent blocking
		TradeQueue:           make(chan map[string]interface{}, 100),
		WatcherTrackingQueue: make(chan map[string]interface{}, 100),
		ResearchQueue:        make(chan map[string]interface{}, 100),
	}
}

// PushTrade sends a trade intent to the TradeQueue.
func (m *Manager) PushTrade(payload map[string]interface{}) {
	m.TradeQueue <- payload
}

// PushTracking sends an execution result to the WatcherTrackingQueue.
func (m *Manager) PushTracking(payload map[string]interface{}) {
	m.WatcherTrackingQueue <- payload
}

// PushResearch sends an event to the ResearchQueue.
func (m *Manager) PushResearch(payload map[string]interface{}) {
	m.ResearchQueue <- payload
}
