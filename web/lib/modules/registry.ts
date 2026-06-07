import type { DecisionModule } from "./types";
import { sendHoldModule } from "./send-hold";
import { stealAttemptModule } from "./steal-attempt";
import { ibbModule } from "./ibb";

export const moduleRegistry: DecisionModule[] = [
  sendHoldModule,
  stealAttemptModule,
  ibbModule,
  // Future modules register here — no other structural changes needed:
  // pinchHitModule,
];

export function getModule(slug: string): DecisionModule | undefined {
  return moduleRegistry.find((m) => m.slug === slug);
}
