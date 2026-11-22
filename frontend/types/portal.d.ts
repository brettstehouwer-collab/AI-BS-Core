export type PortalValue = string | number | boolean | null | PortalValue[] | {[key: string]: PortalValue};
export interface PortalContextValue {values: Record<string, unknown>; update<T extends PortalValue>(key: string, next: import('react').SetStateAction<T>, fallback: T): void; save(): Promise<void>; saving: boolean; savedAt: string | null; dirty: boolean; error: string}

