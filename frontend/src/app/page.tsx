import { Box, Card, Flex, Grid, Heading, Separator, Text } from '@radix-ui/themes'
import { ArrowRightIcon, LoopIcon, MobileIcon, Share2Icon } from '@radix-ui/react-icons'
import FileUploader from '@/components/FileUploader'
import RecentJobs from '@/components/RecentJobs'

const FEATURES = [
  {
    icon: <LoopIcon width={16} height={16} />,
    label: 'Транзакционные циклы',
    desc: 'Обнаружение слоёв (layering)'
  },
  {
    icon: <Share2Icon width={16} height={16} />,
    label: 'Веерное дробление',
    desc: 'Смурфинг (smurfing)'
  },
  {
    icon: <ArrowRightIcon width={16} height={16} />,
    label: 'Транзитные узлы',
    desc: 'Счета-посредники'
  },
  {
    icon: <MobileIcon width={16} height={16} />,
    label: 'Общие устройства',
    desc: 'Связанные клиенты по устройству/IP'
  }
]

export default function Home() {
  return (
    <Flex
      direction="column"
      align="center"
      px="4"
      style={{ minHeight: '100vh', paddingTop: 'clamp(3rem, 12vh, 5rem)', paddingBottom: '4rem' }}
    >
      <Flex direction="column" align="center" gap="7" style={{ maxWidth: 560, width: '100%' }}>
        <Flex direction="column" align="center" gap="2">
          <Heading size="7" align="center">
            AML Graph Visualizer
          </Heading>
          <Text color="gray" align="center" size="3">
            Загрузите CSV с финансовыми транзакциями для обнаружения паттернов отмывания денег —
            циклов, дробления, транзитных узлов и общих устройств.
          </Text>
        </Flex>

        <Box style={{ width: '100%' }}>
          <FileUploader />
        </Box>

        <Separator size="4" />

        <Box style={{ width: '100%' }}>
          <RecentJobs />
        </Box>

        <Grid columns="2" gap="3" style={{ width: '100%' }}>
          {FEATURES.map(({ icon, label, desc }) => (
            <Card key={label} size="1">
              <Flex gap="2" align="start">
                <Box pt="1" style={{ color: 'var(--accent-9)' }}>
                  {icon}
                </Box>
                <Flex direction="column" gap="1">
                  <Text size="2" weight="medium">
                    {label}
                  </Text>
                  <Text size="1" color="gray">
                    {desc}
                  </Text>
                </Flex>
              </Flex>
            </Card>
          ))}
        </Grid>
      </Flex>
    </Flex>
  )
}
