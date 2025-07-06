import React, { useRef, useState } from 'react';
import { UploadedImage } from '../types';

interface ImageUploadProps {
  onImageUpload: (files: File[]) => void;
  uploadedImages: UploadedImage[];
  selectedImages: UploadedImage[];
  onRemoveImage: (imageId: string) => void;
  onToggleSelection: (image: UploadedImage) => void;
}

const ImageUpload: React.FC<ImageUploadProps> = ({
  onImageUpload,
  uploadedImages,
  selectedImages,
  onRemoveImage,
  onToggleSelection
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    const validFiles = Array.from(files).filter(file => {
      const isImage = file.type.startsWith('image/');
      const isValidSize = file.size <= 16 * 1024 * 1024; // 16MB
      return isImage && isValidSize;
    });
    if (validFiles.length > 0) {
      onImageUpload(validFiles);
    }
  };

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
    handleFileSelect(e.dataTransfer.files);
  };

  return (
    <>
      <div className="sidebar-header">
        <div className="sidebar-title">
          <span>Image Upload</span>
        </div>
        {/* <p className="sidebar-subtitle">
          Upload images to use in your conversation
        </p> */}
      </div>

      <div className="upload-area">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
        >
          {/* <div className="upload-icon">📤</div> */}
          <p className="upload-text">
            Drag and drop images here, or click to select files
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn"
          >
            Select Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => handleFileSelect(e.target.files)}
            style={{ display: 'none' }}
          />
        </div>

        <div className="upload-info">
          <p>• Supported formats: PNG, JPG, JPEG, GIF, BMP, WEBP</p>
          <p>• Maximum file size: 16MB</p>
          <p>• Multiple files can be selected</p>
        </div>
      </div>

      <div className="images-list">
        <h4 style={{ fontWeight: 500, color: '#111827', marginBottom: '1rem' }}>
          Available Images ({uploadedImages.length})
        </h4>
        
        {uploadedImages.length === 0 ? (
          <div className="images-empty">
            {/* <div className="images-empty-icon">🖼️</div> */}
            <p className="images-empty-text">No images uploaded yet</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {uploadedImages.map((image) => {
              const isSelected = selectedImages.some(img => img.id === image.id);
              return (
                <div
                  key={image.id}
                  onClick={() => onToggleSelection(image)}
                  style={{
                    position: 'relative',
                    cursor: 'pointer',
                    border: isSelected ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                    borderRadius: '0.25rem',
                    overflow: 'hidden'
                  }}
                >
                  <img
                    src={image.url}
                    alt={image.file.name}
                    style={{
                      width: '4rem',
                      height: '4rem',
                      objectFit: 'cover',
                      opacity: image.isUploading ? 0.5 : 1
                    }}
                  />
                  {image.isUploading && (
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: 'rgba(255, 255, 255, 0.8)'
                    }}>
                      ⟳
                    </div>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveImage(image.id);
                    }}
                    style={{
                      position: 'absolute',
                      top: '0.125rem',
                      right: '0.125rem',
                      width: '1.25rem',
                      height: '1.25rem',
                      backgroundColor: 'rgba(239, 68, 68, 0.8)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '50%',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
};

export default ImageUpload; 