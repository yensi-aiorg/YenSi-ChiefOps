/**
 * ProjectDashboard is the same component as ProjectDetail.
 * The route /projects/:projectId renders ProjectDetail directly, which
 * serves as both the project dashboard (static overview) and the entry
 * point to the custom dashboard tab.
 *
 * This file re-exports ProjectDetail under the ProjectDashboard name
 * for semantic clarity in the router configuration.
 */
export { ProjectDetail as ProjectDashboard } from "./ProjectDetail";
