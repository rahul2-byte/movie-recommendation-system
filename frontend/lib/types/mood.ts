export type Mood =
    | "HAPPY"
    | "DARK"
    | "EMOTIONAL"
    | "ROMANTIC"
    | "INSPIRATIONAL"
    | "THRILLING"

export const MOODS: { label: string; value: Mood }[] = [
    { label: "Happy", value: "HAPPY" },
    { label: "Dark", value: "DARK" },
    { label: "Emotional", value: "EMOTIONAL" },
    { label: "Romantic", value: "ROMANTIC" },
    { label: "Inspirational", value: "INSPIRATIONAL" },
    { label: "Thrilling", value: "THRILLING" },
]
