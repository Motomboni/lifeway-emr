/**
 * Video Call Component
 * 
 * Twilio Video integration for telemedicine consultations.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { logger } from '../../utils/logger';
import styles from '../../styles/VideoCall.module.css';

interface VideoCallProps {
  token: string;
  roomName: string;
  onLeave: () => void;
  onError?: (error: Error) => void;
}

export default function VideoCall({ token, roomName, onLeave, onError }: VideoCallProps) {
  const { user } = useAuth();
  const { showError } = useToast();
  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [localVideoTrack, setLocalVideoTrack] = useState<any>(null);
  const [localAudioTrack, setLocalAudioTrack] = useState<any>(null);
  const [remoteVideoTrack, setRemoteVideoTrack] = useState<any>(null);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [connectionLost, setConnectionLost] = useState<string | null>(null);
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const roomRef = useRef<any>(null);
  const localVideoTrackRef = useRef<any>(null);
  const localAudioTrackRef = useRef<any>(null);
  const remoteVideoTrackRef = useRef<any>(null);

  // Cleanup function to properly release camera and microphone
  const cleanup = useCallback(() => {
    // Only cleanup if we actually have resources to clean up
    const hasResources = 
      remoteVideoTrackRef.current || 
      localVideoTrackRef.current || 
      localAudioTrackRef.current || 
      roomRef.current;
    
    if (!hasResources) {
      return; // Nothing to clean up
    }
    
    logger.debug('Cleaning up video call resources...');
    
    // Detach and stop remote video track
    if (remoteVideoTrackRef.current) {
      try {
        if (remoteVideoRef.current) {
          remoteVideoTrackRef.current.detach(remoteVideoRef.current);
        }
        remoteVideoTrackRef.current.stop();
      } catch (error) {
        console.error('Error cleaning up remote video track:', error);
      }
      remoteVideoTrackRef.current = null;
      setRemoteVideoTrack(null);
    }
    
    // Detach and stop local video track
    if (localVideoTrackRef.current) {
      try {
        if (localVideoRef.current) {
          localVideoTrackRef.current.detach(localVideoRef.current);
        }
        localVideoTrackRef.current.stop();
      } catch (error) {
        console.error('Error cleaning up local video track:', error);
      }
      localVideoTrackRef.current = null;
      setLocalVideoTrack(null);
    }
    
    // Stop local audio track
    if (localAudioTrackRef.current) {
      try {
        localAudioTrackRef.current.stop();
      } catch (error) {
        console.error('Error cleaning up audio track:', error);
      }
      localAudioTrackRef.current = null;
      setLocalAudioTrack(null);
    }
    
    // Disconnect from room
    if (roomRef.current) {
      try {
        roomRef.current.disconnect();
      } catch (error) {
        console.error('Error disconnecting room:', error);
      }
      roomRef.current = null;
    }
    
    // Clear video elements
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
      localVideoRef.current.load(); // Reset video element
    }
    if (remoteVideoRef.current) {
      remoteVideoRef.current.srcObject = null;
      remoteVideoRef.current.load(); // Reset video element
    }
    
    logger.debug('Video call cleanup complete');
  }, []);

  // Attach local video track to video element when both are available
  useEffect(() => {
    if (!localVideoTrack) {
      return;
    }

    // Wait for video element to be ready
    const attachVideo = () => {
      if (localVideoRef.current && localVideoTrack) {
        logger.debug('Attaching local video track to video element');
        try {
          // Check if already attached
          if (localVideoRef.current.srcObject) {
            logger.debug('Video element already has srcObject, detaching first');
            localVideoTrack.detach();
          }
          
          localVideoTrack.attach(localVideoRef.current);
          logger.debug('Local video track attached successfully');
          
          // Ensure video plays
          const playVideo = () => {
            if (localVideoRef.current) {
              localVideoRef.current.play()
                .then(() => {
                  logger.debug('Local video playing');
                })
                .catch((error: any) => {
                  console.error('Error playing local video:', error);
                  // Try to play again after a short delay
                  setTimeout(() => {
                    if (localVideoRef.current) {
                      localVideoRef.current.play().catch((err: any) => {
                        console.error('Retry play failed:', err);
                      });
                    }
                  }, 100);
                });
            }
          };
          
          // Try to play immediately
          playVideo();
          
          // Also try when video element is ready
          if (localVideoRef.current) {
            localVideoRef.current.onloadedmetadata = playVideo;
          }
        } catch (error) {
          console.error('Error attaching local video track:', error);
        }
      } else {
        // Video element not ready yet, try again shortly
        setTimeout(attachVideo, 50);
      }
    };
    
    attachVideo();
    
    return () => {
      if (localVideoTrack && localVideoRef.current) {
        try {
          localVideoTrack.detach(localVideoRef.current);
        } catch (error) {
          console.error('Error detaching local video:', error);
        }
      }
    };
  }, [localVideoTrack]);

  // Attach remote video track to video element when both are available
  useEffect(() => {
    if (!remoteVideoTrack) {
      return;
    }

    // Wait for video element to be ready
    const attachVideo = () => {
      if (remoteVideoRef.current && remoteVideoTrack) {
        logger.debug('Attaching remote video track to video element');
        try {
          // Check if already attached
          if (remoteVideoRef.current.srcObject) {
            logger.debug('Remote video element already has srcObject, detaching first');
            remoteVideoTrack.detach();
          }
          
          remoteVideoTrack.attach(remoteVideoRef.current);
          logger.debug('Remote video track attached successfully');
          
          // Ensure video plays
          const playVideo = () => {
            if (remoteVideoRef.current) {
              remoteVideoRef.current.play()
                .then(() => {
                  logger.debug('Remote video playing');
                })
                .catch((error: any) => {
                  console.error('Error playing remote video:', error);
                  // Try to play again after a short delay
                  setTimeout(() => {
                    if (remoteVideoRef.current) {
                      remoteVideoRef.current.play().catch((err: any) => {
                        console.error('Retry play failed:', err);
                      });
                    }
                  }, 100);
                });
            }
          };
          
          // Try to play immediately
          playVideo();
          
          // Also try when video element is ready
          if (remoteVideoRef.current) {
            remoteVideoRef.current.onloadedmetadata = playVideo;
          }
        } catch (error) {
          console.error('Error attaching remote video track:', error);
        }
      } else {
        // Video element not ready yet, try again shortly
        setTimeout(attachVideo, 50);
      }
    };
    
    attachVideo();
    
    return () => {
      if (remoteVideoTrack && remoteVideoRef.current) {
        try {
          remoteVideoTrack.detach(remoteVideoRef.current);
        } catch (error) {
          console.error('Error detaching remote video:', error);
        }
      }
    };
  }, [remoteVideoTrack]);

  // Main connection effect
  useEffect(() => {
    let mounted = true;
    
    const connectToRoom = async () => {
      try {
        // Dynamically import Twilio Video SDK and reduce console noise (track-stalled, ICE, heartbeat)
        const twilioVideo = await import('twilio-video');
        const { connect, createLocalVideoTrack, createLocalAudioTrack } = twilioVideo;
        if (typeof (twilioVideo as any).Logger?.setLogLevel === 'function') {
          (twilioVideo as any).Logger.setLogLevel('error');
        }
        logger.debug('Creating local video and audio tracks...');
        // Create local tracks with error handling
        let videoTrack: any = null;
        let audioTrack: any = null;
        
        try {
          videoTrack = await createLocalVideoTrack({
            width: 1280,
            height: 720,
            frameRate: 24,
          });
          logger.debug('Local video track created');
        } catch (videoError: any) {
          console.error('Failed to create video track:', videoError);
          showError('Failed to access camera: ' + (videoError.message || 'Permission denied'));
          setIsConnecting(false);
          return;
        }
        
        try {
          audioTrack = await createLocalAudioTrack();
          logger.debug('Local audio track created');
        } catch (audioError: any) {
          console.error('Failed to create audio track:', audioError);
          showError('Failed to access microphone: ' + (audioError.message || 'Permission denied'));
          // Continue without audio if video works
        }
        
        if (!mounted) {
          if (videoTrack) videoTrack.stop();
          if (audioTrack) audioTrack.stop();
          return;
        }
        
        // Store tracks in refs for cleanup
        localVideoTrackRef.current = videoTrack;
        localAudioTrackRef.current = audioTrack;
        setLocalVideoTrack(videoTrack);
        setLocalAudioTrack(audioTrack);
        
        logger.debug('Connecting to room:', roomName);
        // Connect to room
        const room = await connect(token, {
          name: roomName,
          tracks: audioTrack ? [videoTrack, audioTrack] : [videoTrack],
        });
        
        if (!mounted) {
          room.disconnect();
          if (videoTrack) videoTrack.stop();
          if (audioTrack) audioTrack.stop();
          return;
        }
        
        roomRef.current = room;
        setIsConnecting(false);
        setIsConnected(true);
        logger.debug('Connected to room successfully');
        
        // Handle remote participants
        room.on('participantConnected', (participant: any) => {
          logger.debug('Participant connected:', participant.identity);
          participant.tracks.forEach((publication: any) => {
            if (publication.track) {
              handleTrackSubscribed(publication.track);
            }
          });
          
          participant.on('trackSubscribed', handleTrackSubscribed);
        });
        
        // Handle participant disconnected
        room.on('participantDisconnected', (participant: any) => {
          logger.debug('Participant disconnected:', participant.identity);
          if (remoteVideoTrackRef.current) {
            try {
              if (remoteVideoRef.current) {
                remoteVideoTrackRef.current.detach(remoteVideoRef.current);
              }
              remoteVideoTrackRef.current.stop();
            } catch (error) {
              console.error('Error cleaning up remote track on disconnect:', error);
            }
            remoteVideoTrackRef.current = null;
          }
          setRemoteVideoTrack(null);
        });
        
        // Handle disconnection (user leave, network loss, heartbeat timeout, etc.)
        room.on('disconnected', (room: any, error: any) => {
          logger.debug('Room disconnected', error?.message || '');
          setIsConnected(false);
          setConnectionLost(error?.message || 'Connection lost. You can return to the visit.');
          cleanup();
        });
        
      } catch (error: any) {
        console.error('Failed to connect to video room:', error);
        setIsConnecting(false);
        showError(error.message || 'Failed to connect to video call');
        cleanup();
        if (onError) {
          onError(error);
        }
      }
    };
    
    const handleTrackSubscribed = (track: any) => {
      logger.debug('Track subscribed:', track.kind);
      if (track.kind === 'video') {
        remoteVideoTrackRef.current = track;
        setRemoteVideoTrack(track);
      }
    };
    
    connectToRoom();
    
    // Handle page unload to ensure cleanup
    const handleBeforeUnload = () => {
      cleanup();
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      mounted = false;
      window.removeEventListener('beforeunload', handleBeforeUnload);
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, roomName]); // cleanup is stable (useCallback with empty deps), so we don't need it in deps
  
  const toggleVideo = async () => {
    if (localVideoTrackRef.current) {
      if (isVideoEnabled) {
        localVideoTrackRef.current.disable();
        logger.debug('Video disabled');
      } else {
        localVideoTrackRef.current.enable();
        logger.debug('Video enabled');
      }
      setIsVideoEnabled(!isVideoEnabled);
    }
  };
  
  const toggleAudio = async () => {
    if (localAudioTrackRef.current) {
      if (isAudioEnabled) {
        localAudioTrackRef.current.disable();
        logger.debug('Audio disabled');
      } else {
        localAudioTrackRef.current.enable();
        logger.debug('Audio enabled');
      }
      setIsAudioEnabled(!isAudioEnabled);
    }
  };
  
  const handleLeave = () => {
    logger.debug('User leaving call...');
    cleanup();
    onLeave();
  };
  
  if (isConnecting) {
    return (
      <div className={styles.videoCallContainer}>
        <div className={styles.connecting}>
          <div className={styles.spinner}></div>
          <p>Connecting to video call...</p>
        </div>
      </div>
    );
  }
  
  if (connectionLost) {
    return (
      <div className={styles.videoCallContainer}>
        <div className={styles.connecting}>
          <p className={styles.connectionLostMessage}>{connectionLost}</p>
          <button type="button" className={styles.controlButton} onClick={() => { setConnectionLost(null); onLeave(); }}>
            Return to visit
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className={styles.videoCallContainer}>
      <div className={styles.videoGrid}>
        {/* Remote Video */}
        <div className={styles.remoteVideoContainer}>
          {remoteVideoTrack ? (
            <video
              ref={remoteVideoRef}
              autoPlay
              playsInline
              className={styles.remoteVideo}
            />
          ) : (
            <div className={styles.waitingForParticipant}>
              <p>Waiting for participant to join...</p>
            </div>
          )}
        </div>
        
        {/* Local Video */}
        <div className={styles.localVideoContainer}>
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            className={styles.localVideo}
            style={{ display: isVideoEnabled ? 'block' : 'none' }}
          />
          {!isVideoEnabled && (
            <div className={styles.videoDisabled}>
              <p>Camera Off</p>
            </div>
          )}
          <div className={styles.localVideoLabel}>
            {user?.first_name} {user?.last_name} (You)
          </div>
        </div>
      </div>
      
      {/* Controls */}
      <div className={styles.controls}>
        <button
          onClick={toggleVideo}
          className={`${styles.controlButton} ${!isVideoEnabled ? styles.disabled : ''}`}
          title={isVideoEnabled ? 'Turn off camera' : 'Turn on camera'}
        >
          {isVideoEnabled ? '📹' : '📹❌'}
        </button>
        
        <button
          onClick={toggleAudio}
          className={`${styles.controlButton} ${!isAudioEnabled ? styles.disabled : ''}`}
          title={isAudioEnabled ? 'Mute microphone' : 'Unmute microphone'}
        >
          {isAudioEnabled ? '🎤' : '🎤❌'}
        </button>
        
        <button
          onClick={handleLeave}
          className={`${styles.controlButton} ${styles.leaveButton}`}
          title="Leave call"
        >
          📞 Leave Call
        </button>
      </div>
      
      {isConnected && (
        <div className={styles.status}>
          <span className={styles.statusIndicator}></span>
          Connected
        </div>
      )}
    </div>
  );
}
