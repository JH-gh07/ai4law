import type { ClauseNode, NumberingStyle } from "../../lib/document-ir";

function numberToken(style: NumberingStyle | undefined, position: number): string {
  // The schema default is "decimal"; undefined means "decimal", not "none".
  const resolved: NumberingStyle = style ?? "decimal";
  switch (resolved) {
    case "decimal":
      return `${position}.`;
    case "lower_alpha":
      return `(${String.fromCharCode(96 + position)})`;
    case "lower_roman":
      return `${toRoman(position).toLowerCase()}.`;
    case "none":
      return "";
  }
}

function toRoman(value: number): string {
  const table: Array<[number, string]> = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"],
    [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
    [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
  ];
  let remaining = value;
  let result = "";
  for (const [numeral, symbol] of table) {
    while (remaining >= numeral) {
      result += symbol;
      remaining -= numeral;
    }
  }
  return result;
}

function ClauseLine({ clause, position, depth }: { clause: ClauseNode; position: number; depth: number }) {
  const token = numberToken(clause.numbering_style, position);
  const heading = `${token} ${clause.text}`.trim();
  return (
    <li className="clause-node" style={{ marginLeft: depth > 0 ? `${depth * 1.25}rem` : undefined }}>
      <span className="clause-node-text">{heading}</span>
      {clause.children && clause.children.length > 0 ? (
        <ol className="clause-children">
          {clause.children.map((child, index) => (
            <ClauseLine key={child.node_id} clause={child} position={index + 1} depth={depth + 1} />
          ))}
        </ol>
      ) : null}
    </li>
  );
}

export function ClauseTree({ clauses }: { clauses: ClauseNode[] }) {
  return (
    <ol className="clause-tree">
      {clauses.map((clause, index) => (
        <ClauseLine key={clause.node_id} clause={clause} position={index + 1} depth={0} />
      ))}
    </ol>
  );
}
