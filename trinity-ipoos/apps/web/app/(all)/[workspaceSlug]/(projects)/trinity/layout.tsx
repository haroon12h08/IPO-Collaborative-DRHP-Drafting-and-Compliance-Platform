/**
 * Trinity IPO Preparation — Layout
 * Wraps the Trinity wizard within Plane's workspace context.
 */

import { Outlet } from "react-router";

export default function TrinityLayout() {
  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      <Outlet />
    </div>
  );
}
