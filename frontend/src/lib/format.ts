export const inr = (n: number) => "₹" + n.toLocaleString("en-IN");
export const lakhs = (n: number) => "₹" + (n / 100000).toFixed(1) + "L";
export const lpa = (n: number | null | undefined) => (n == null ? "—" : `₹${n} LPA`);
