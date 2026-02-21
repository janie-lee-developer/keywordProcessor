import React from 'react';

// keyword, description, url, and timestamp are all variables —
// swap them out for any data shape you like.
function KeywordCard({ keyword, description, url, timestamp }) {
  const formattedTime = timestamp
    ? new Date(timestamp).toLocaleString()
    : null;

  return (
    <div className="keyword-card">
      <div className="keyword-card__header">
        <h2 className="keyword-card__term">{keyword}</h2>
        {formattedTime && (
          <span className="keyword-card__timestamp">{formattedTime}</span>
        )}
      </div>

      <p className="keyword-card__definition">{description}</p>

      {url && (
        <a
          className="keyword-card__source"
          href={url}
          target="_blank"
          rel="noopener noreferrer"
        >
          View source &rarr;
        </a>
      )}
    </div>
  );
}

export default KeywordCard;
