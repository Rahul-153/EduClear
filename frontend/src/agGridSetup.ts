import {
  CellStyleModule, ClientSideRowModelApiModule, ClientSideRowModelModule, ColumnApiModule, ColumnAutoSizeModule, ModuleRegistry,
  NumberFilterModule, RenderApiModule, RowApiModule, RowStyleModule, TextFilterModule, ValidationModule,
} from "ag-grid-community";

// Only the AG Grid modules this app uses. ValidationModule reports a missing module in dev builds.
ModuleRegistry.registerModules([
  ClientSideRowModelModule, ClientSideRowModelApiModule, ColumnApiModule, RowApiModule, RenderApiModule, TextFilterModule, NumberFilterModule,
  ColumnAutoSizeModule, CellStyleModule, RowStyleModule,
  ...(import.meta.env.DEV || import.meta.env.VITE_AG_VALIDATE ? [ValidationModule] : []),
]);
