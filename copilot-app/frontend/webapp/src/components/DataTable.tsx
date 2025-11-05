import React, { useMemo } from 'react';
import { DataGrid, GridColDef, GridToolbar, GridRenderCellParams, GridValueGetterParams } from '@mui/x-data-grid';
import { Paper, Typography, Box, CircularProgress, Alert } from '@mui/material';
import { ErrorOutline as ErrorIcon } from '@mui/icons-material';
import { safeArray } from '../utils/safeAccess';

interface DataTableProps<T = any> {
  title?: string;
  columns: GridColDef[];
  rows: T[];
  loading?: boolean;
  error?: string;
  toolbar?: boolean;
  pageSizeOptions?: number[];
  defaultPageSize?: number;
  disableRowSelection?: boolean;
  height?: number;
  width?: string | number;
}

const DataTable = <T extends Record<string, any> = any>({
  title,
  columns,
  rows = [],
  loading = false,
  error,
  toolbar = true,
  pageSizeOptions = [10, 25, 50, 100],
  defaultPageSize = 25,
  disableRowSelection = true,
  height = 400,
  width = '100%'
}: DataTableProps<T>) => {
  const safeRows = useMemo(() => safeArray(rows), [rows]);

  if (loading) {
    return (
      <Paper sx={{ p: 2, height: height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2 }}>
        <Alert severity="error" icon={<ErrorIcon />}>
          <Typography variant="subtitle1">Erreur de chargement de la table</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
      </Paper>
    );
  }

  if (!safeRows || safeRows.length === 0) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="body1" align="center" color="text.secondary">
          Aucune donnée disponible
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ height: height, width: width }}>
      {title && (
        <Box sx={{ borderBottom: 1, borderColor: 'divider', p: 1 }}>
          <Typography variant="h6" component="h3" sx={{ pl: 1 }}>
            {title}
          </Typography>
        </Box>
      )}
      <Box sx={{ height: title ? height - 48 : height, width: '100%' }}>
        <DataGrid
          rows={safeRows}
          columns={columns}
          loading={loading}
          slots={{
            toolbar: toolbar ? GridToolbar : undefined,
          }}
          slotProps={{
            toolbar: {
              showQuickFilter: true,
              quickFilterProps: { debounceMs: 500 },
            },
          }}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: defaultPageSize,
              },
            },
          }}
          pageSizeOptions={pageSizeOptions}
          disableRowSelectionOnClick={disableRowSelection}
          getRowId={(row) => row.id || row._id || JSON.stringify(row)}
        />
      </Box>
    </Paper>
  );
};

export default DataTable;