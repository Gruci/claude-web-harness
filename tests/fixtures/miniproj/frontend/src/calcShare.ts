export function share(part: number, total: number): number {
  return total === 0 ? 0 : part / total;
}
