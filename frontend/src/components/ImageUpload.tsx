import React, { useState, useRef } from 'react';
import { Upload, X, Image as ImageIcon, Check } from 'lucide-react';
import type { UploadedImage } from '../types';
import { apiService } from '../services/api';

interface ImageUploadProps {
  onImageUpload: (images: UploadedImage[]) => void;
  uploadedImages: UploadedImage[];
  selectedImages: UploadedImage[];
  onRemoveImage: (image: UploadedImage) => void;
  onToggleSelection: (image: UploadedImage) => void;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({
  onImageUpload,
  uploadedImages,
  selectedImages,
  onRemoveImage,
  onToggleSelection,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileSelect(files);
  };

  const handleFileSelect = async (files: File[]) => {
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length === 0) {
      alert('Please select valid image files');
      return;
    }

    const newImages: UploadedImage[] = imageFiles.map(file => ({
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      file,
      url: URL.createObjectURL(file),
      isUploading: true,
    }));

    onImageUpload(newImages);

    // Upload files to backend
    try {
      const response = await apiService.uploadFiles(imageFiles);
      const updatedImages = newImages.map((img, index) => ({
        ...img,
        isUploading: false,
        uploadedPath: response.files[index]?.path,
      }));
      onImageUpload(updatedImages);
    } catch (error) {
      console.error('Upload failed:', error);
      const failedImages = newImages.map(img => ({
        ...img,
        isUploading: false,
        uploadError: 'Upload failed',
      }));
      onImageUpload(failedImages);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          <ImageIcon className="w-5 h-5" />
          Images
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Upload images to use in your conversation
        </p>
      </div>

      {/* Upload Area */}
      <div className="p-4">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`upload-dropzone cursor-pointer ${isDragging ? 'dragging' : ''}`}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-3" />
          <p className="text-sm text-gray-600 mb-2">
            Drag and drop images here, or click to select
          </p>
          <button className="text-sm bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors">
            Select Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => handleFileSelect(Array.from(e.target.files || []))}
            className="hidden"
          />
        </div>

        <div className="mt-3 text-xs text-gray-500">
          <p>• Supported: PNG, JPG, JPEG, GIF, BMP, WEBP</p>
          <p>• Max size: 16MB per file</p>
          <p>• Multiple files supported</p>
        </div>
      </div>

      {/* Images List */}
      <div className="flex-1 overflow-y-auto border-t border-gray-200">
        {uploadedImages.length === 0 ? (
          <div className="p-8 text-center">
            <ImageIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No images uploaded yet</p>
          </div>
        ) : (
          <div className="p-4 space-y-3">
            {uploadedImages.map((image) => {
              const isSelected = selectedImages.some(selected => selected.id === image.id);
              
              return (
                <div
                  key={image.id}
                  className={`relative group border-2 rounded-lg overflow-hidden cursor-pointer transition-all ${
                    isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => onToggleSelection(image)}
                >
                  <div className="aspect-square bg-gray-100">
                    <img
                      src={image.url}
                      alt="Uploaded"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  
                  {image.isUploading && (
                    <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                      <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  )}
                  
                  {image.uploadError && (
                    <div className="absolute inset-0 bg-red-500 bg-opacity-75 flex items-center justify-center">
                      <span className="text-white text-xs font-medium">Failed</span>
                    </div>
                  )}
                  
                  {isSelected && (
                    <div className="absolute top-2 right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveImage(image);
                    }}
                    className="absolute top-2 left-2 w-6 h-6 bg-red-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                  
                  <div className="p-2 bg-white">
                    <p className="text-xs text-gray-600 truncate">{image.file.name}</p>
                    <p className="text-xs text-gray-400">
                      {(image.file.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}; 