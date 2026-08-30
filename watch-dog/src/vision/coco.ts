import '@tensorflow/tfjs-node';
import * as tf from '@tensorflow/tfjs-node';
import * as cocoSsd from '@tensorflow-models/coco-ssd';

export type DogDetection = {
  score: number;
  box: [x: number, y: number, width: number, height: number];
  frameWidth: number;
  frameHeight: number;
};

export class CocoDogDetector {
  private model?: cocoSsd.ObjectDetection;

  async load(): Promise<void> {
    this.model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
  }

  async detect(jpeg: Buffer, minConfidence: number): Promise<DogDetection | null> {
    if (!this.model) throw new Error('Detector model is not loaded');

    const image = tf.node.decodeImage(jpeg, 3);
    try {
      const [height, width] = image.shape;
      const predictions = await this.model.detect(image as tf.Tensor3D);
      const dog = predictions
        .filter((p) => p.class === 'dog' && p.score >= minConfidence)
        .sort((a, b) => b.score - a.score)[0];

      if (!dog) return null;
      return {
        score: dog.score,
        box: dog.bbox as [number, number, number, number],
        frameWidth: width,
        frameHeight: height,
      };
    } finally {
      image.dispose();
    }
  }
}
