export interface ParsedScreenplay {beats: import('./domain').ScreenplayBeat[]; html: string}
export interface DraftContent {project: string; content: string; revision?: string; fdx_document?: any}
export interface CapturedDraft extends DraftContent {edit: number; branch?: string}
export interface RecoveryDraft extends DraftContent {key: string; savedAt: string; edit?: number; branch?: string}
export interface SaveProblem {project?: string; message: string; reviewOnly?: boolean; conflict?: boolean}
export interface Character {name: string; gender?: string; role?: string; voice_tag?: string; vocal_tone?: string; vocal_pitch?: string; accent?: string; personality?: string; bio?: string; speaking_style?: string}
