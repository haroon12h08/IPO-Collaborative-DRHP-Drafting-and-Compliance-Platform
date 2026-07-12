/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function PlaneLogo({ className }: ISvgIcons) {
  return (
    <span className={`font-bold text-xl whitespace-nowrap tracking-tighter text-primary ${className}`}>
      T
    </span>
  );
}
