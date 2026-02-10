/**
 * Utility functions for offline-first image upload.
 */
import { v4 as uuidv4 } from 'uuid';

/**
 * Calculate SHA-256 checksum of a file.
 */
export async function calculateChecksum(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

/**
 * Generate a unique image UUID.
 */
export function generateImageUuid(): string {
  return uuidv4();
}

/**
 * Generate a unique session UUID.
 */
export function generateSessionUuid(): string {
  return uuidv4();
}

/**
 * Get device information.
 */
export function getDeviceInfo(): Record<string, any> {
  return {
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Get device ID (from localStorage or generate new).
 */
export function getDeviceId(): string {
  const storageKey = 'radiology_device_id';
  let deviceId = localStorage.getItem(storageKey);
  
  if (!deviceId) {
    deviceId = generateSessionUuid();
    localStorage.setItem(storageKey, deviceId);
  }
  
  return deviceId;
}

/**
 * Store image locally in IndexedDB.
 */
export async function storeImageLocally(
  imageUuid: string,
  file: File,
  metadata: {
    radiologyOrderId: number;
    filename: string;
    checksum: string;
    mimeType: string;
    imageMetadata?: Record<string, any>;
  }
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('RadiologyImages', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction(['images'], 'readwrite');
      const store = transaction.objectStore('images');
      
      const imageData = {
        uuid: imageUuid,
        file: file,
        metadata: metadata,
        storedAt: new Date().toISOString(),
      };
      
      const addRequest = store.add(imageData, imageUuid);
      addRequest.onsuccess = () => resolve();
      addRequest.onerror = () => reject(addRequest.error);
    };
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('images')) {
        db.createObjectStore('images', { keyPath: 'uuid' });
      }
    };
  });
}

/**
 * Get locally stored image.
 */
export async function getLocalImage(imageUuid: string): Promise<File | null> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('RadiologyImages', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction(['images'], 'readonly');
      const store = transaction.objectStore('images');
      const getRequest = store.get(imageUuid);
      
      getRequest.onsuccess = () => {
        const result = getRequest.result;
        resolve(result ? result.file : null);
      };
      getRequest.onerror = () => reject(getRequest.error);
    };
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('images')) {
        db.createObjectStore('images', { keyPath: 'uuid' });
      }
    };
  });
}

/**
 * Delete locally stored image.
 */
export async function deleteLocalImage(imageUuid: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('RadiologyImages', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction(['images'], 'readwrite');
      const store = transaction.objectStore('images');
      const deleteRequest = store.delete(imageUuid);
      
      deleteRequest.onsuccess = () => resolve();
      deleteRequest.onerror = () => reject(deleteRequest.error);
    };
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('images')) {
        db.createObjectStore('images', { keyPath: 'uuid' });
      }
    };
  });
}

/**
 * Get all pending local images.
 */
export async function getPendingLocalImages(): Promise<Array<{
  uuid: string;
  file: File;
  metadata: any;
}>> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('RadiologyImages', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction(['images'], 'readonly');
      const store = transaction.objectStore('images');
      const getAllRequest = store.getAll();
      
      getAllRequest.onsuccess = () => {
        resolve(getAllRequest.result || []);
      };
      getAllRequest.onerror = () => reject(getAllRequest.error);
    };
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('images')) {
        db.createObjectStore('images', { keyPath: 'uuid' });
      }
    };
  });
}

