import type { FC } from 'react';

interface ScoreBadgeProps {
  label: string;
  score: number;
  isPrimary?: boolean;
}

const ScoreBadge: FC<ScoreBadgeProps> = ({ label, score, isPrimary = false }) => {
  const getScoreClass = (value: number): string => {
    if (value >= 0.7) return 'score-high';
    if (value >= 0.5) return 'score-medium';
    return 'score-low';
  };

  const scoreClass = getScoreClass(score);
  const badgeClass = `score-badge ${scoreClass} ${isPrimary ? 'primary' : ''}`;

  return (
    <div className={badgeClass}>
      <span className="score-label">{label}</span>
      <span className="score-value">{score?.toFixed(2) ?? 'N/A'}</span>
    </div>
  );
};

export default ScoreBadge;
