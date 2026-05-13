"use client";

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function TagEditor({ value, onChange }: Props) {
  return (
    <label className="field">
      <span>Tags</span>
      <input
        value={value}
        placeholder="kafka, interview"
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
