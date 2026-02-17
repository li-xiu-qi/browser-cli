import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const UserComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();

  // 模拟重力弹跳效果
  const bounce = spring({
    frame,
    fps,
    config: {
      damping: 12, // 阻尼适中，让它多弹几次
      stiffness: 150,
      mass: 0.8,
    },
    durationInFrames: 60,
  });

  // 将 spring 值 (0-1) 映射到 Y 轴位置
  // 0 -> 顶部 (0)
  // 1 -> 底部 (height - 球体大小)
  const ballSize = 150;
  const floorY = height / 2 + 300; // 地面位置
  const startY = height / 2 - 400; // 起始下落位置
  
  // 简单的插值：从上落到下
  // 注意：单纯的 spring 是单向的，这里做一个简单的“落地-回弹”视觉欺骗
  // 实际上 spring 更适合做类似 toggle 的动作。
  // 为了做物理弹跳，通常用 Math.abs(Math.cos(t)) 或者专门的物理引擎。
  // 但为了演示 spring 效果，我们让球“弹入”画面中心。
  
  const y = startY + (floorY - startY) * bounce;
  const scale = 1 + (bounce > 0.8 ? 0.1 * Math.sin(frame * 0.5) : 0); // 落地微颤

  return (
    <AbsoluteFill style={{ backgroundColor: '#1e1e1e', justifyContent: 'center', alignItems: 'center' }}>
      {/* 地面 */}
      <div style={{
          position: 'absolute',
          top: floorY + ballSize/2,
          width: '60%',
          height: 10,
          backgroundColor: '#555',
          borderRadius: 5
      }} />

      {/* 红球 */}
      <div
        style={{
          width: ballSize,
          height: ballSize,
          borderRadius: '50%',
          backgroundColor: '#ff4757',
          boxShadow: '0 10px 30px rgba(255, 71, 87, 0.5)',
          transform: `translateY(${y - height/2}px) scale(${1})`, // 居中修正
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <span style={{ color: 'white', fontWeight: 'bold', fontSize: 24 }}>Bounce</span>
      </div>
      
      <div style={{
          position: 'absolute',
          bottom: 100,
          color: '#888',
          fontFamily: 'monospace'
      }}>
          Rendered with Local Tool
      </div>
    </AbsoluteFill>
  );
};