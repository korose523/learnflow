import React from 'react';

interface SkeletonProps {
  width?: number | string;
  height?: number;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
  dark?: boolean;
  className?: string;
}

const roundedMap = { sm: '4px', md: '8px', lg: '12px', full: '9999px' };

export function Skeleton({ width = '100%', height = 16, rounded = 'md', dark = false, className = '' }: SkeletonProps) {
  return (
    <div
      className={`${dark ? 'skeleton-dark' : 'skeleton'} ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: `${height}px`,
        borderRadius: roundedMap[rounded],
      }}
    />
  );
}

export function CardSkeleton({ dark = false }: { dark?: boolean }) {
  return (
    <div className={dark ? 'card-dark' : 'card'} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Skeleton width="60%" height={20} dark={dark} />
      <Skeleton width="100%" height={12} dark={dark} />
      <Skeleton width="80%" height={12} dark={dark} />
      <Skeleton width="40%" height={32} rounded="lg" dark={dark} />
    </div>
  );
}
