import { Agent, routeAgentRequest, callable } from "agents";

export interface Env {
  AI_BS_AGENT: DurableObjectNamespace;
}

type AgentState = {
  clientId: string;
  activeWorkloads: number;
  lastTelemetryPing: string;
};

export class AIBSAgent extends Agent<Env, AgentState> {
  initialState: AgentState = {
    clientId: "stehouwer_publishing",
    activeWorkloads: 0,
    lastTelemetryPing: new Date().toISOString()
  };

  validateStateChange(nextState: AgentState) {
    if (!nextState.clientId) {
      throw new Error("Client ID is required for multi-tenant isolation.");
    }
  }

  @callable()
  async recordTelemetry(payload: { clientId?: string; status: string }) {
    const tenant = payload.clientId || "stehouwer_publishing";
    this.setState({
      ...this.state,
      clientId: tenant,
      lastTelemetryPing: new Date().toISOString()
    });
    return { status: "acknowledged", tenant, timestamp: this.state.lastTelemetryPing };
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return routeAgentRequest(request, env) ?? new Response("AI-BS Edge Agent Active", { status: 200 });
  }
};
