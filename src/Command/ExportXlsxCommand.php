<?php

namespace App\Command;

use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Helper\MemberXlsExporter;
use App\Repository\MemberSubscriptionRepository;
use App\Repository\SubscriptionRepository;
use Doctrine\Persistence\ManagerRegistry;
use PhpOffice\PhpSpreadsheet\Writer\Exception;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand(
    name: 'app:export-xlsx',
    description: 'Export members to xlsx file'
)]
class ExportXlsxCommand extends Command
{
    public function __construct(protected ManagerRegistry $managerRegistry, protected MemberXlsExporter $memberXlsImporter)
    {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addArgument('source', InputArgument::REQUIRED, 'File source')
            ->addOption('subscription', null, InputOption::VALUE_REQUIRED, 'Subscribe users');
    }

    /**
     * @throws Exception
     */
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $src = $input->getArgument('source');

        if (null === $src) {
            return 1;
        }

        $subscriptionName = $input->getOption('subscription');
        /** @var SubscriptionRepository $subscriptionRepo */
        $subscriptionRepo = $this->managerRegistry->getRepository(Subscription::class);
        $subscription = $subscriptionRepo->getCurrentSubscription($subscriptionName);

        $output->writeln('Subscription '.$subscription?->getName());
        if (null === $subscription) {
            $output->writeln('No subscription found');

            return 1;
        }

        /** @var MemberSubscriptionRepository $memberSubscriptionRepo */
        $memberSubscriptionRepo = $this->managerRegistry->getRepository(MemberSubscription::class);
        $memberSubscriptions = $memberSubscriptionRepo->getActiveSubscriptions($subscription);
        $this->memberXlsImporter->exportToFile($subscription, $memberSubscriptions, $src);

        return Command::SUCCESS;
    }
}
