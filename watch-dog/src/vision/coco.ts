import * as tf from '@tensorflow/tfjs';
import * as cocoSsd from '@tensorflow-models/coco-ssd';
import jpeg from 'jpeg-js';

export type DogDetection = {
  score: number;
  box: [x: number, y: number, width: number, height: number];
  frameWidth: number;
  frameHeight: number;
};

export class CocoDogDetector {
  private model?: cocoSsd.ObjectDetection;

  async load(): Promise<void> {
    await tf.setBackend('cpu');
    await tf.ready();
    this.model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
  }

  async detect(jpegBuffer: Buffer, minConfidence: number): Promise<DogDetection | null> {
    if (!this.model) throw new Error('Detector model is not loaded');

    const decoded = jpeg.decode(jpegBuffer, { useTArray: true, formatAsRGBA: true });
    const rgba = decoded.data;
    const rgb = new Uint8Array(decoded.width * decoded.height * 3);

    for (let src = 0, dst = 0; src < rgba.length; src += 4) {
      rgb[dst++] = rgba[src];
      rgb[dst++] = rgba[src + 1];
      rgb[dst++] = rgba[src + 2];
    }

    const image = tf.tensor3d(rgb, [decoded.height, decoded.width, 3], 'int32');
    try {
      const predictions = await this.model.detect(image);
      const dog = predictions
        .filter((p) => p.class === 'dog' && p.score >= minConfidence)
        .sort((a, b) => b.score - a.score)[0];

      if (!dog) return null;
      return {
        score: dog.score,
        box: dog.bbox as [number, number, number, number],
        frameWidth: decoded.width,
        frameHeight: decoded.height,
      };
    } finally {
      image.dispose();
    }
  }
}
