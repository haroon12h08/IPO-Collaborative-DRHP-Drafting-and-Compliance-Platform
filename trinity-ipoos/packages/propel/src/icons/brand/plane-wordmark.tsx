/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function PlaneWordmark({ className }: ISvgIcons) {
  return (
    <span className={`font-semibold text-base whitespace-nowrap tracking-tight text-primary ${className}`}>
      Trinity Intelligence
    </span>
  );
}
