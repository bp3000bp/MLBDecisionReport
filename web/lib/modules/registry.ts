import type { DecisionModule } from "./types";
import { sendHoldModule } from "./send-hold";

export const moduleRegistry: DecisionModule[] = [
  sendHoldModule,
  // Future modules register here — no other structural changes needed:
  // stealAttemptModule,
  // ibbModule,
  // pinchHitModule,
];

export function getModule(slug: string): DecisionModule | undefined {
  return moduleRegistry.find((m) => m.slug === slug);
}
