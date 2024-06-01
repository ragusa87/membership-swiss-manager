<?php

namespace App\Command;

use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Helper\MemberMatcher;
use App\Helper\MemberTableFormatter;
use App\Helper\MemberXlsImporter;
use App\Repository\MemberSubscriptionRepository;
use Doctrine\Persistence\ManagerRegistry;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Helper\Table;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:import-xlsx',
    description: 'Add a short description for your command',
)]
class ImportXlsxCommand extends Command
{
    public function __construct(protected ManagerRegistry $managerRegistry, protected MemberXlsImporter $memberXlsImporter, protected MemberTableFormatter $formatter, protected MemberMatcher $matcher)
    {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addArgument('source', InputArgument::REQUIRED, 'File source')
            ->addOption('force', null, InputOption::VALUE_NONE, 'Force import')
            ->addOption('subscription', null, InputOption::VALUE_REQUIRED, 'Subscribe users');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $src = $input->getArgument('source');

        if (null === $src) {
            return 1;
        }
        // Parse members from xlsx

        $members = $this->memberXlsImporter->parse($src);
        // Try to match each member with an existing member
        $matches = array_map(fn (Member $member) => $this->matcher->find($member), $members->getArrayCopy());

        // Display the result of matches
        $this->formatter->fillMatches(new Table($output), $matches)->render();

        $subscriptionName = $input->getOption('subscription');
        $subscription = null;
        if (null !== $subscriptionName) {
            $subscription = $this->managerRegistry->getRepository(Subscription::class)->findOneBy(['name' => $subscriptionName]);
            $io->block(sprintf('%s subscription %s', null === $subscription ? 'create' : 'assign', $subscriptionName));
        }

        $force = $input->getOption('force');
        if (!$force) {
            $io->warning('Users are just displayed, use the force option to import');

            return Command::SUCCESS;
        }

        $mergedUsers = new \WeakMap();
        /**
         * @var Member[] $users
         */
        $users = [];
        /**
         * @var Member[] $users
         */
        $toVerify = [];

        $nbCreated = 0;
        // Merge each matched user (without handling children)
        // Note that the list concern every imported member, child and parents.
        foreach ($matches as $match) {
            // Skip not matching entities
            if (null === $match->getResult()) {
                // Create imported user as no merge are needed
                $this->managerRegistry->getManager()->persist($match->getMember());
                $users[] = $match->getMember();
                ++$nbCreated;
                // The user's parent can be wrong, check that later
                if (null !== $match->getMember()->getParent()) {
                    $toVerify[] = $match->getMember();
                }
                continue;
            }
            // Merge the existing user with the imported one
            $match->getResult()->merge($match->getMember());
            // Store user for subscription
            $users[] = $match->getResult();

            // The parent might be wrong, check that later
            if (null !== $match->getMember()->getParent()) {
                $toVerify[] = $match->getMember();
            }
            if (null !== $match->getResult()->getParent()) {
                $toVerify[] = $match->getResult();
            }
            // Be sure the imported one is not going to be saved
            $this->managerRegistry->getManager()->detach($match->getMember());

            // Keep trace of the merged users
            $this->managerRegistry->getManager()->persist($match->getResult());
            $mergedUsers->offsetSet($match->getMember(), $match->getResult());
        }

        // Use the merged parent if any
        while (($user = array_pop($toVerify)) !== null) {
            /** @var Member $user */
            if (null == $user->getParent()) {
                continue;
            }
            $ref = $user->getParent();
            if ($mergedUsers->offsetExists($ref)) {
                $user->setParent($mergedUsers->offsetGet($ref));
            }
        }

        if ($subscriptionName) {
            $subscription = $this->createSubscription($subscriptionName, $subscription);
            $this->createMemberSubscription($subscription, $users);
        }

        // $match->getResult() !== null ? $this->managerRegistry->getManager()->persist($match->getResult()) : null;
        $this->managerRegistry->getManager()->flush();
        // Success
        $io->success(sprintf('%s user created, %s merged', $nbCreated, $mergedUsers->count()));

        return Command::SUCCESS;
    }

    /**
     * @param array<Member> $members
     */
    private function createMemberSubscription(Subscription $subscription, array $members): void
    {
        /** @var MemberSubscriptionRepository $repo */
        $repo = $this->managerRegistry->getRepository(MemberSubscription::class);
        $repo->subscribe($subscription, $members);
    }

    private function createSubscription(string $subscriptionName, ?Subscription $subscription): Subscription
    {
        if ($subscription) {
            return $subscription;
        }
        $subscription = new Subscription();
        $subscription->setName($subscriptionName);
        $this->managerRegistry->getManager()->persist($subscription);

        return $subscription;
    }
}
