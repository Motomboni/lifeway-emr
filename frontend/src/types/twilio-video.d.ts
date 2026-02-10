/**
 * Type declarations for twilio-video
 * 
 * This file provides TypeScript type definitions for the twilio-video package.
 * The package may not include complete type definitions, so we declare the
 * essential types we use.
 */

declare module 'twilio-video' {
  export interface LocalVideoTrack {
    stop(): void;
    attach(element: HTMLElement | HTMLMediaElement): void;
    detach(): void;
  }

  export interface LocalAudioTrack {
    stop(): void;
    attach(element: HTMLElement | HTMLMediaElement): void;
    detach(): void;
  }

  export interface RemoteVideoTrack {
    stop(): void;
    attach(element: HTMLElement | HTMLMediaElement): void;
    detach(): void;
  }

  export interface RemoteAudioTrack {
    stop(): void;
    attach(element: HTMLElement | HTMLMediaElement): void;
    detach(): void;
  }

  export interface RemoteParticipant {
    videoTracks: Map<string, RemoteVideoTrackPublication>;
    audioTracks: Map<string, RemoteAudioTrackPublication>;
    sid: string;
    identity: string;
  }

  export interface RemoteVideoTrackPublication {
    track: RemoteVideoTrack | null;
    trackSid: string;
    isSubscribed: boolean;
  }

  export interface RemoteAudioTrackPublication {
    track: RemoteAudioTrack | null;
    trackSid: string;
    isSubscribed: boolean;
  }

  export interface Room {
    disconnect(): void;
    localParticipant: {
      videoTracks: Map<string, LocalVideoTrackPublication>;
      audioTracks: Map<string, LocalAudioTrackPublication>;
      publishTrack(track: LocalVideoTrack | LocalAudioTrack): Promise<LocalTrackPublication>;
      unpublishTrack(track: LocalVideoTrack | LocalAudioTrack): Promise<LocalTrackPublication>;
    };
    participants: Map<string, RemoteParticipant>;
    sid: string;
    name: string;
    state: 'connected' | 'disconnected' | 'reconnecting';
    on(event: string, listener: (...args: any[]) => void): void;
    off(event: string, listener?: (...args: any[]) => void): void;
  }

  export interface LocalTrackPublication {
    track: LocalVideoTrack | LocalAudioTrack;
    trackSid: string;
  }

  export interface ConnectOptions {
    name: string;
    audio?: boolean;
    video?: boolean;
    tracks?: (LocalVideoTrack | LocalAudioTrack)[];
  }

  export function connect(
    token: string,
    options?: ConnectOptions
  ): Promise<Room>;

  export function createLocalVideoTrack(
    options?: any
  ): Promise<LocalVideoTrack>;

  export function createLocalAudioTrack(
    options?: any
  ): Promise<LocalAudioTrack>;
}
