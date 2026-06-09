import type { Candidate } from "../api/client";

interface CandidateTableProps {
  candidates: Candidate[];
  selectedSymbol?: string;
  onSelect: (candidate: Candidate) => void;
}

export function CandidateTable({ candidates, selectedSymbol, onSelect }: CandidateTableProps) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Symbol</th>
            <th>Name</th>
            <th>Score</th>
            <th>Confidence</th>
            <th>Quality</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => (
            <tr
              className={candidate.symbol === selectedSymbol ? "selected" : ""}
              key={candidate.symbol}
              onClick={() => onSelect(candidate)}
            >
              <td>{candidate.rank}</td>
              <td className="symbol">{candidate.symbol}</td>
              <td>{candidate.name}</td>
              <td>{candidate.opportunity_score.toFixed(1)}</td>
              <td>{candidate.confidence.toFixed(2)}</td>
              <td>
                <span className={`pill ${candidate.data_quality}`}>{candidate.data_quality}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

