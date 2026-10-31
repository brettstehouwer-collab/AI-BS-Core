export interface LoginTelemetryUser { email?: string | null; displayName?: string | null; uid?: string; photoURL?: string | null }
export interface LocalTrustState { enabled: boolean; allowedUsers: string[] }
export interface AutomationJob { id: string; status: string; action: string; command: string[]; cwd?: string | null; created_at: string; started_at?: string | null; finished_at?: string | null; canceled: boolean; exit_code?: number | null; stdout: string; stderr: string; [key: string]: unknown }
export interface AutomationJobRequest { action: string; parameters: Record<string, unknown>; cwd?: string; timeout: number; sandbox: boolean; user_email?: string }
export interface AutomationBridge {
  listJobs(): Promise<{ jobs: AutomationJob[] }>;
  runJob(payload: AutomationJobRequest): Promise<AutomationJob>;
  getJob(jobId: string): Promise<AutomationJob>;
  cancelJob(jobId: string): Promise<unknown>;
  getLocalTrustState(): Promise<LocalTrustState>;
  setLocalTrustState(payload: LocalTrustState): Promise<LocalTrustState>;
}
export type LegacyGetUserMedia = (constraints: MediaStreamConstraints, success: (stream: MediaStream) => void, failure: (error: DOMException) => void) => void;
export interface SpeechRecognitionResultEvent {resultIndex?: number; results: ArrayLike<ArrayLike<{transcript: string; confidence?: number}> & {isFinal?: boolean}>}
export interface SpeechRecognitionController {lang: string; continuous: boolean; interimResults: boolean; start(): void; stop(): void; abort?(): void; onstart: (() => void) | null; onresult: ((event: SpeechRecognitionResultEvent) => void) | null; onerror: ((event: {error: string; message?: string}) => void) | null; onend: (() => void) | null}
export interface SpeechRecognitionConstructor {new (): SpeechRecognitionController}
interface ConnectionInformation { effectiveType?: string; downlink?: number; rtt?: number }
declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
    Capacitor?: { isNativePlatform?: () => boolean };
    aibsAutomation?: AutomationBridge;
    __aibsLastHostFile?: string;
    __aibs_toggle_mom_mode?: () => void;
    __setBackendUrl?: (url: string) => void;
    FIREBASE_APPCHECK_DEBUG_TOKEN?: boolean | string;
    env?: { BACKEND_URL?: string };
    webkitAudioContext?: typeof AudioContext;
    sendDashboardAnalyticsBeacon?: (eventType?: string, customData?: unknown) => void;
    sendDashboardLoginNotification?: (user: LoginTelemetryUser) => Promise<Response | undefined>;
  }
  interface Navigator {
    standalone?: boolean;
    getUserMedia?: LegacyGetUserMedia;
    webkitGetUserMedia?: LegacyGetUserMedia;
    mozGetUserMedia?: LegacyGetUserMedia;
    connection?: ConnectionInformation;
    mozConnection?: ConnectionInformation;
    webkitConnection?: ConnectionInformation;
    deviceMemory?: number;
  }
}

// Chromium directory picker attributes used by the host file workflow.
declare module 'react' {
  interface CSSProperties { [key: `--${string}`]: string | number | undefined }
  interface InputHTMLAttributes<T> {
    webkitdirectory?: string;
    directory?: string;
  }
}



