import { VideoFormat, VideoMetadata } from '../types/project';

export const MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024; // 100 MB
export const MAX_VIDEO_DURATION_SECONDS = 60; // 60 seconds
export const ALLOWED_VIDEO_FORMATS: VideoFormat[] = ['mp4', 'mov', 'webm'];

export const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export interface ValidationResult<T = void> {
  isValid: boolean;
  error?: string;
  data?: T;
}

export function validateVideoFile(file: File): ValidationResult {
  const extension = file.name.split('.').pop()?.toLowerCase();
  
  const isValidFormat = 
    file.type.includes('mp4') || 
    file.type.includes('quicktime') || 
    file.type.includes('webm') ||
    ALLOWED_VIDEO_FORMATS.includes(extension as VideoFormat);

  if (!isValidFormat) {
    return {
      isValid: false,
      error: `Unsupported format: .${extension || 'unknown'}. BollySwap accepts MP4, MOV, or WebM video files.`,
    };
  }

  if (file.size > MAX_VIDEO_SIZE_BYTES) {
    return {
      isValid: false,
      error: `Video size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds the 100MB studio limit for Phase 1.`,
    };
  }

  return { isValid: true };
}

export function extractVideoMetadata(file: File): Promise<ValidationResult<VideoMetadata>> {
  return new Promise((resolve) => {
    const basicValidation = validateVideoFile(file);
    if (!basicValidation.isValid) {
      resolve({ isValid: false, error: basicValidation.error });
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';

    video.onloadedmetadata = () => {
      const duration = video.duration;
      const width = video.videoWidth || 1920;
      const height = video.videoHeight || 1080;

      if (duration > MAX_VIDEO_DURATION_SECONDS) {
        URL.revokeObjectURL(objectUrl);
        resolve({
          isValid: false,
          error: `Video duration (${Math.round(duration)}s) exceeds maximum allowed 60 seconds. Please trim your clip.`,
        });
        return;
      }

      const extension = file.name.split('.').pop()?.toLowerCase() as VideoFormat;
      const format: VideoFormat = ['mp4', 'mov', 'webm'].includes(extension) ? extension : 'mp4';

      const metadata: VideoMetadata = {
        name: file.name,
        url: objectUrl,
        sizeBytes: file.size,
        durationSec: duration,
        width,
        height,
        fps: 30,
        format,
        isDemoSample: false,
      };

      resolve({ isValid: true, data: metadata });
    };

    video.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({
        isValid: false,
        error: 'Unable to decode video stream. Please ensure the file is an uncorrupted MP4, MOV, or WebM.',
      });
    };

    video.src = objectUrl;
  });
}

export function validateImageFile(file: File): ValidationResult {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return {
      isValid: false,
      error: 'Unsupported image format. Please upload a high-resolution JPG or PNG file.',
    };
  }

  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return {
      isValid: false,
      error: `Image file exceeds maximum allowable 10MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB).`,
    };
  }

  return { isValid: true };
}

