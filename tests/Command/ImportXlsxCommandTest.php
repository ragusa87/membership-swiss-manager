<?php

namespace App\Tests\Command;

use Symfony\Bundle\FrameworkBundle\Console\Application;
use Symfony\Bundle\FrameworkBundle\Test\KernelTestCase;
use Symfony\Component\Console\Tester\CommandTester;

class ImportXlsxCommandTest extends KernelTestCase
{
    public function testExecute(): void
    {
        $kernel = static::createKernel();
        $kernel->boot();

        $application = new Application($kernel);
        $application->setAutoExit(false);

        $command = $application->find('app:import-xlsx');
        $commandTester = new CommandTester($command);
        $commandTester->execute([
            'source' => __DIR__.'/../../src/DataFixtures/members_fixtures.xlsx',
        ]);

        $output = $commandTester->getDisplay();
        $this->assertStringContainsString('just displayed', $output);
    }
}
