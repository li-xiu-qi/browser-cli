import React from 'react';
import { Composition } from 'remotion';
import { UserComposition } from './UserComposition';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="UserComposition"
				component={UserComposition}
				durationInFrames={150}
				fps={30}
				width={1080}
				height={1080}
			/>
		</>
	);
};