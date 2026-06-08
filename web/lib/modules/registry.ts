import type { DecisionModule } from "./types";
import { sendHoldModule } from "./send-hold";
import { stealAttemptModule } from "./steal-attempt";
import { ibbModule } from "./ibb";
import { pinchHitModule } from "./pinch-hit";

export const moduleRegistry: DecisionModule[] = [
  sendHoldModule,
  stealAttemptModule,
  ibbModule,
  pinchHitModule,
];

export function getModule(slug: string): DecisionModule | undefined {
  return moduleRegistry.find((m) => m.slug === slug);
}
