// AudioWorkletProcessor is a browser platform API omitted from lib.webworker.
// Declare the processor/port contract used by public/vst-worklet.js; this file
// is included only by tsconfig.worklet.json.
interface AudioWorkletProcessorOptions {
  numberOfInputs?: number;
  numberOfOutputs?: number;
  outputChannelCount?: number[];
  parameterData?: Record<string, number>;
  processorOptions?: unknown;
}

declare abstract class AudioWorkletProcessor {
  readonly port: MessagePort;
  constructor(options?: AudioWorkletProcessorOptions);
  abstract process(
    inputs: Float32Array[][],
    outputs: Float32Array[][],
    parameters: Record<string, Float32Array>,
  ): boolean;
}

declare function registerProcessor(
  name: string,
  processorConstructor: new (options?: AudioWorkletProcessorOptions) => AudioWorkletProcessor,
): void;
