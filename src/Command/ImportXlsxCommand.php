<?php

namespace App\Command;

use App\Helper\MemberXlsImporter;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Logger\ConsoleLogger;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:import-xlsx',
    description: 'Add a short description for your command',
)]
class ImportXlsxCommand extends Command
{
    public function __construct(protected MemberXlsImporter $memberXlsImporter)
    {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addArgument('source', InputArgument::OPTIONAL, 'File source');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $src = $input->getArgument('source');

        $this->memberXlsImporter->setLogger(new ConsoleLogger($output));
        $users = $this->memberXlsImporter->import($src);

        $io->success(sprintf('%s user imported', count($users)));

        return Command::SUCCESS;
    }
}
