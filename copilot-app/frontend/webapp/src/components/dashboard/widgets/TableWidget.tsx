import type { ReactNode } from 'react';
import { Card, ScrollArea, Table, Text } from '@mantine/core';

export function TableWidget({
  title,
  rows,
  columns,
  height = 340,
  empty,
  loading,
}: {
  title?: string;
  rows: any[];
  columns: { key: string; header: string; render?: (value: any, row: any) => ReactNode }[];
  height?: number;
  empty?: boolean;
  loading?: boolean;
}) {
  return (
    <Card withBorder shadow="sm" data-testid="table">
      {title && (
        <Text fw={600} mb="xs">
          {title}
        </Text>
      )}
      {empty && !loading ? (
        <Text c="dimmed">Aucune donnée</Text>
      ) : (
        <ScrollArea h={height} type="auto" offsetScrollbars>
          <Table striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                {columns.map((column) => (
                  <Table.Th key={column.key}>{column.header}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((row, rowIndex) => (
                <Table.Tr key={rowIndex}>
                  {columns.map((column) => (
                    <Table.Td key={column.key}>
                      {column.render ? column.render(row[column.key], row) : String(row[column.key] ?? '—')}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      )}
    </Card>
  );
}
