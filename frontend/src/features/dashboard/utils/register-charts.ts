import { AllCommunityModule, ModuleRegistry } from "ag-charts-community";

// AG Charts 14 renders nothing until its modules are registered. Importing this
// file from every chart component registers them once, before the first render.
ModuleRegistry.registerModules([AllCommunityModule]);
