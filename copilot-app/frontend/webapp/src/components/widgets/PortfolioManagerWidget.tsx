/**
 * PortfolioManagerWidget - Manage portfolios/watchlists
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-002 - Frontend integration
 */
import { useState } from 'react'
import {
  Card,
  Title,
  Text,
  Button,
  Modal,
  TextInput,
  Textarea,
  Badge,
  Group,
  Stack,
  ActionIcon,
  Menu,
  Loader,
  Alert,
  MultiSelect,
} from '@mantine/core'
import {
  IconPlus,
  IconEdit,
  IconTrash,
  IconDotsVertical,
  IconAlertCircle,
  IconBriefcase,
  IconChartLine,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import {
  usePortfolios,
  useCreatePortfolio,
  useUpdatePortfolio,
  useDeletePortfolio,
  useAddTickers,
  useRemoveTicker,
  type Portfolio,
  type PortfolioCreateRequest,
  type PortfolioUpdateRequest,
} from '@/hooks/usePortfolios'
import { PerformanceCharts } from '@/components/portfolios/PerformanceCharts'

// ============================================================================
// Main Widget
// ============================================================================

export function PortfolioManagerWidget() {
  const { data: portfolios = [], isLoading, error } = usePortfolios()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [performanceModalOpen, setPerformanceModalOpen] = useState(false)
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null)

  // Handlers
  const handleCreate = () => {
    setCreateModalOpen(true)
  }

  const handleEdit = (portfolio: Portfolio) => {
    setSelectedPortfolio(portfolio)
    setEditModalOpen(true)
  }

  const handleDelete = (portfolio: Portfolio) => {
    setSelectedPortfolio(portfolio)
    setDeleteModalOpen(true)
  }

  const handleViewPerformance = (portfolio: Portfolio) => {
    setSelectedPortfolio(portfolio)
    setPerformanceModalOpen(true)
  }

  if (isLoading) {
    return (
      <Card p="lg">
        <Group justify="center" p="xl">
          <Loader size="lg" />
          <Text c="dimmed">Loading portfolios...</Text>
        </Group>
      </Card>
    )
  }

  if (error) {
    return (
      <Card p="lg">
        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
          Failed to load portfolios: {error.message}
        </Alert>
      </Card>
    )
  }

  return (
    <>
      <Card p="lg">
        <Group justify="space-between" mb="md">
          <Group>
            <IconBriefcase size={24} />
            <Title order={3}>Portfolios & Watchlists</Title>
            <Badge size="lg" color="blue">
              {portfolios.length}
            </Badge>
          </Group>
          <Button leftSection={<IconPlus size={16} />} onClick={handleCreate}>
            Create Watchlist
          </Button>
        </Group>

        {portfolios.length === 0 ? (
          <Stack align="center" gap="md" py="xl">
            <IconBriefcase size={48} color="gray" />
            <Text c="dimmed" size="lg">
              No portfolios yet
            </Text>
            <Text c="dimmed" size="sm">
              Create your first watchlist to organize tickers
            </Text>
            <Button leftSection={<IconPlus size={16} />} onClick={handleCreate}>
              Create Watchlist
            </Button>
          </Stack>
        ) : (
          <Stack gap="md">
            {portfolios.map((portfolio) => (
              <PortfolioCard
                key={portfolio.id}
                portfolio={portfolio}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onViewPerformance={handleViewPerformance}
              />
            ))}
          </Stack>
        )}
      </Card>

      {/* Create Modal */}
      <CreatePortfolioModal
        opened={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
      />

      {/* Edit Modal */}
      {selectedPortfolio && (
        <EditPortfolioModal
          opened={editModalOpen}
          portfolio={selectedPortfolio}
          onClose={() => {
            setEditModalOpen(false)
            setSelectedPortfolio(null)
          }}
        />
      )}

      {/* Delete Confirmation Modal */}
      {selectedPortfolio && (
        <DeleteConfirmationModal
          opened={deleteModalOpen}
          portfolio={selectedPortfolio}
          onClose={() => {
            setDeleteModalOpen(false)
            setSelectedPortfolio(null)
          }}
        />
      )}

      {/* Performance Modal */}
      {selectedPortfolio && (
        <Modal
          opened={performanceModalOpen}
          onClose={() => {
            setPerformanceModalOpen(false)
            setSelectedPortfolio(null)
          }}
          title={`${selectedPortfolio.name} - Performance`}
          size="xl"
        >
          <PerformanceCharts portfolio={selectedPortfolio} />
        </Modal>
      )}
    </>
  )
}

// ============================================================================
// Portfolio Card
// ============================================================================

interface PortfolioCardProps {
  portfolio: Portfolio
  onEdit: (portfolio: Portfolio) => void
  onDelete: (portfolio: Portfolio) => void
  onViewPerformance: (portfolio: Portfolio) => void
}

function PortfolioCard({ portfolio, onEdit, onDelete, onViewPerformance }: PortfolioCardProps) {
  const removeTicker = useRemoveTicker()

  const handleRemoveTicker = (ticker: string) => {
    removeTicker.mutate(
      { id: portfolio.id, ticker },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Ticker removed',
            message: `${ticker} removed from ${portfolio.name}`,
            color: 'green',
          })
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: error.message,
            color: 'red',
          })
        },
      }
    )
  }

  return (
    <Card withBorder p="md">
      <Group justify="space-between" mb="sm">
        <Group>
          <IconBriefcase size={20} />
          <div>
            <Text fw={600} size="lg">
              {portfolio.name}
            </Text>
            {portfolio.description && (
              <Text size="sm" c="dimmed">
                {portfolio.description}
              </Text>
            )}
          </div>
        </Group>

        <Menu position="bottom-end">
          <Menu.Target>
            <ActionIcon variant="subtle">
              <IconDotsVertical size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item leftSection={<IconChartLine size={14} />} onClick={() => onViewPerformance(portfolio)}>
              View Performance
            </Menu.Item>
            <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => onEdit(portfolio)}>
              Edit
            </Menu.Item>
            <Menu.Item
              leftSection={<IconTrash size={14} />}
              color="red"
              onClick={() => onDelete(portfolio)}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>

      <Group gap="xs" mb="sm">
        {portfolio.tickers.length === 0 ? (
          <Text size="sm" c="dimmed">
            No tickers yet
          </Text>
        ) : (
          portfolio.tickers.map((ticker) => (
            <Badge
              key={ticker}
              size="lg"
              variant="light"
              rightSection={
                <ActionIcon
                  size="xs"
                  variant="transparent"
                  onClick={() => handleRemoveTicker(ticker)}
                >
                  ×
                </ActionIcon>
              }
            >
              {ticker}
            </Badge>
          ))
        )}
      </Group>

      <Group justify="space-between" mt="sm">
        <Group gap="md">
          <Text size="xs" c="dimmed">
            {portfolio.tickers.length} tickers
          </Text>
          <Text size="xs" c="dimmed">
            Updated {new Date(portfolio.updated_at).toLocaleDateString()}
          </Text>
        </Group>
        <Button
          size="xs"
          variant="light"
          leftSection={<IconChartLine size={14} />}
          onClick={() => onViewPerformance(portfolio)}
        >
          View Performance
        </Button>
      </Group>
    </Card>
  )
}

// ============================================================================
// Create Portfolio Modal
// ============================================================================

interface CreatePortfolioModalProps {
  opened: boolean
  onClose: () => void
}

function CreatePortfolioModal({ opened, onClose }: CreatePortfolioModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [tickers, setTickers] = useState<string[]>([])
  
  const createMutation = useCreatePortfolio()

  const handleSubmit = () => {
    if (!name.trim()) {
      notifications.show({
        title: 'Validation Error',
        message: 'Portfolio name is required',
        color: 'red',
      })
      return
    }

    const request: PortfolioCreateRequest = {
      name: name.trim(),
      description: description.trim(),
      tickers,
    }

    createMutation.mutate(request, {
      onSuccess: () => {
        notifications.show({
          title: 'Success',
          message: `Portfolio "${name}" created`,
          color: 'green',
        })
        setName('')
        setDescription('')
        setTickers([])
        onClose()
      },
      onError: (error) => {
        notifications.show({
          title: 'Error',
          message: error.message,
          color: 'red',
        })
      },
    })
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Create Portfolio" size="lg">
      <Stack gap="md">
        <TextInput
          label="Name"
          placeholder="e.g. Tech Watchlist"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
          required
        />

        <Textarea
          label="Description"
          placeholder="Optional description"
          value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
          minRows={2}
        />

        <MultiSelect
          label="Tickers"
          placeholder="Enter tickers (e.g. AAPL, MSFT, GOOGL)"
          data={[]}
          value={tickers}
          onChange={setTickers}
          searchable
          creatable
          getCreateLabel={(query) => `+ Add ${query.toUpperCase()}`}
          onCreate={(query) => {
            const ticker = query.toUpperCase()
            setTickers([...tickers, ticker])
            return ticker
          }}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="subtle" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={createMutation.isPending}>
            Create
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

// ============================================================================
// Edit Portfolio Modal
// ============================================================================

interface EditPortfolioModalProps {
  opened: boolean
  portfolio: Portfolio
  onClose: () => void
}

function EditPortfolioModal({ opened, portfolio, onClose }: EditPortfolioModalProps) {
  const [name, setName] = useState(portfolio.name)
  const [description, setDescription] = useState(portfolio.description)
  const [tickers, setTickers] = useState<string[]>(portfolio.tickers)
  
  const updateMutation = useUpdatePortfolio()

  const handleSubmit = () => {
    if (!name.trim()) {
      notifications.show({
        title: 'Validation Error',
        message: 'Portfolio name is required',
        color: 'red',
      })
      return
    }

    const request: PortfolioUpdateRequest = {
      name: name.trim(),
      description: description.trim(),
      tickers,
    }

    updateMutation.mutate(
      { id: portfolio.id, data: request },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: `Portfolio "${name}" updated`,
            color: 'green',
          })
          onClose()
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: error.message,
            color: 'red',
          })
        },
      }
    )
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Edit Portfolio" size="lg">
      <Stack gap="md">
        <TextInput
          label="Name"
          placeholder="e.g. Tech Watchlist"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
          required
        />

        <Textarea
          label="Description"
          placeholder="Optional description"
          value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
          minRows={2}
        />

        <MultiSelect
          label="Tickers"
          placeholder="Enter tickers (e.g. AAPL, MSFT, GOOGL)"
          data={tickers}
          value={tickers}
          onChange={setTickers}
          searchable
          creatable
          getCreateLabel={(query) => `+ Add ${query.toUpperCase()}`}
          onCreate={(query) => {
            const ticker = query.toUpperCase()
            setTickers([...tickers, ticker])
            return ticker
          }}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="subtle" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={updateMutation.isPending}>
            Save Changes
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

// ============================================================================
// Delete Confirmation Modal
// ============================================================================

interface DeleteConfirmationModalProps {
  opened: boolean
  portfolio: Portfolio
  onClose: () => void
}

function DeleteConfirmationModal({ opened, portfolio, onClose }: DeleteConfirmationModalProps) {
  const deleteMutation = useDeletePortfolio()

  const handleConfirm = () => {
    deleteMutation.mutate(portfolio.id, {
      onSuccess: () => {
        notifications.show({
          title: 'Portfolio deleted',
          message: `"${portfolio.name}" has been deleted`,
          color: 'green',
        })
        onClose()
      },
      onError: (error) => {
        notifications.show({
          title: 'Error',
          message: error.message,
          color: 'red',
        })
      },
    })
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Delete Portfolio" size="md">
      <Stack gap="md">
        <Alert icon={<IconAlertCircle size={16} />} color="red">
          Are you sure you want to delete "{portfolio.name}"? This action cannot be undone.
        </Alert>

        <Text size="sm" c="dimmed">
          This portfolio contains {portfolio.tickers.length} tickers.
        </Text>

        <Group justify="flex-end" mt="md">
          <Button variant="subtle" onClick={onClose}>
            Cancel
          </Button>
          <Button color="red" onClick={handleConfirm} loading={deleteMutation.isPending}>
            Delete Portfolio
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
