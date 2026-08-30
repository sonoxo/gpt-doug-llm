declare module 'jpeg-js' {
  export type DecodeOptions = {
    useTArray?: boolean;
    formatAsRGBA?: boolean;
  };

  export type DecodedImage = {
    width: number;
    height: number;
    data: Uint8Array;
  };

  const jpeg: {
    decode(data: Uint8Array | Buffer, options?: DecodeOptions): DecodedImage;
  };

  export default jpeg;
}
