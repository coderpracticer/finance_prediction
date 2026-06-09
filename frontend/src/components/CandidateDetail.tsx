import type { Candidate } from "../api/client";
import { ChatPanel } from "./ChatPanel";

interface CandidateDetailProps {
  candidate?: Candidate;
}

export function CandidateDetail({ candidate }: CandidateDetailProps) {
  if (!candidate) {
    return <section className="detail empty">暂无候选标的。运行筛选后会在这里显示研究解释。</section>;
  }

  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <div className="eyebrow">{candidate.market}</div>
          <h2>
            {candidate.symbol} <span>{candidate.name}</span>
          </h2>
        </div>
        <div className="score">{candidate.opportunity_score.toFixed(1)}</div>
      </div>

      <p className="thesis">{candidate.thesis}</p>

      <h3>Factors</h3>
      <div className="factor-list">
        {candidate.factors.map((factor) => (
          <div className="factor" key={factor.name}>
            <div className="factor-top">
              <span>{factor.group}</span>
              <strong>{factor.score.toFixed(1)}</strong>
            </div>
            <div className="bar">
              <div style={{ width: `${factor.score}%` }} />
            </div>
            <p>{factor.evidence}</p>
          </div>
        ))}
      </div>

      <h3>Risks</h3>
      <ul className="risks">
        {candidate.risks.map((risk) => (
          <li key={risk}>{risk}</li>
        ))}
      </ul>

      <ChatPanel symbol={candidate.symbol} />
    </section>
  );
}
