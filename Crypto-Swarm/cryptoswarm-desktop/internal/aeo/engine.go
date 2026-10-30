package aeo

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

const (
	OllamaEndpoint = "http://127.0.0.1:11434/api/generate"
	DefaultModel   = "llama3" // Assuming they have a standard model, if not, might need a generic or let user configure. We'll use llama3 as a safe default for modern ollama
)

type AeoRequest struct {
	Title   string   `json:"title"`
	Author  string   `json:"author"`
	Prompts []string `json:"prompts"`
}

type OllamaRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

type OllamaResponse struct {
	Response string `json:"response"`
}

type PromptResult struct {
	Query      string `json:"query"`
	Ranking    int    `json:"ranking"`
	Visibility string `json:"visibility"`
}

type AeoReport struct {
	OverallScore int            `json:"overall_score"`
	Prompts      []PromptResult `json:"prompts"`
	Suggestions  []string       `json:"suggestions"`
}

func generateLLMResponse(prompt string) (string, error) {
	reqBody := OllamaRequest{
		Model:  DefaultModel,
		Prompt: prompt,
		Stream: false,
	}
	
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return "", err
	}

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Post(OllamaEndpoint, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("ollama API returned status %d", resp.StatusCode)
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	var oResp OllamaResponse
	if err := json.Unmarshal(bodyBytes, &oResp); err != nil {
		return "", err
	}

	return oResp.Response, nil
}

func checkVisibility(llmResponse string, targetTitle string) (int, string) {
	lowerResp := strings.ToLower(llmResponse)
	targetLower := strings.ToLower(targetTitle)

	if targetLower != "" && strings.Contains(lowerResp, targetLower) {
		return 1, "High"
	}
	return 0, "None"
}

func getStrategies(title string, author string) []string {
	prompt := fmt.Sprintf("I am the author of a book called '%s' by %s. What are 3 short, actionable Answer Engine Optimization (AEO) strategies I can use to get my book recommended more by AI platforms like ChatGPT? For example, what specific keywords should I encourage readers to use in reviews? Return ONLY a JSON array of 3 strings.", title, author)
	
	resp, err := generateLLMResponse(prompt)
	if err != nil {
		return []string{
			"Encourage reviewers to use descriptive keywords.",
			"Publish blog posts answering common questions related to your book.",
			"Update metadata on Amazon and Goodreads.",
		}
	}

	// Try to extract JSON array
	start := strings.Index(resp, "[")
	end := strings.LastIndex(resp, "]")
	
	if start != -1 && end != -1 && end > start {
		jsonStr := resp[start : end+1]
		var suggestions []string
		if err := json.Unmarshal([]byte(jsonStr), &suggestions); err == nil && len(suggestions) > 0 {
			return suggestions
		}
	}

	return []string{
		"Encourage reviewers to use descriptive keywords.",
		"Publish blog posts answering common questions related to your book.",
		"Update metadata on Amazon and Goodreads.",
	}
}

// GenerateLiveReport queries the local Ollama instance for live AEO tracking dynamically
func GenerateLiveReport(req AeoRequest) AeoReport {
	var wg sync.WaitGroup
	results := make([]PromptResult, len(req.Prompts))
	
	// Test each query in parallel against the LLM
	for i, query := range req.Prompts {
		wg.Add(1)
		go func(index int, q string) {
			defer wg.Done()
			
			resp, err := generateLLMResponse(q)
			if err != nil {
				// Fallback if LLM is down or missing model
				results[index] = PromptResult{Query: q, Ranking: 0, Visibility: "Error"}
				return
			}
			
			rank, vis := checkVisibility(resp, req.Title)
			results[index] = PromptResult{Query: q, Ranking: rank, Visibility: vis}
		}(i, query)
	}

	wg.Wait()

	// Get strategies
	suggestions := getStrategies(req.Title, req.Author)

	// Calculate overall score based on visibility
	score := 45 // baseline
	for _, r := range results {
		if r.Visibility == "High" {
			score += 15
		}
	}
	if score > 100 {
		score = 98
	}

	return AeoReport{
		OverallScore: score,
		Prompts:      results,
		Suggestions:  suggestions,
	}
}
