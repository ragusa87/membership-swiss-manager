<?php

namespace App\Tests\Helper;

use App\Helper\AddressConverterService;
use App\Helper\MemberXlsImporter;
use PHPUnit\Framework\TestCase;
use Symfony\Component\ErrorHandler\BufferingLogger;

class MemberXlsImporterTest extends TestCase
{
    public function testImport(): void
    {
        $logger = new BufferingLogger();
        $importer = new MemberXlsImporter(new AddressConverterService(), $logger);

        $result = $importer->parse(__DIR__.'/../../src/DataFixtures/members_fixtures.xlsx');
        // Clear logs
        $logger->cleanLogs();

        // 23 user are parsed
        $this->assertCount(23, $result);

        // Yannick Humbert-Droz's parent is Jara Schnider
        $this->assertEquals($result[2]->getParent(), $result[1]);

        // Klara Ballouhey's parent is Rodrigo Scheurer
        $this->assertEquals('Klara Ballouhey', $result[7]->getFullname());
        $this->assertEquals('Klara', $result[7]->getFirstname());
        $this->assertEquals('Rodrigo Scheurer', $result[6]->getFullname());
        $this->assertNotNull($result[7]->getParent(), 'Ballouhey Klara should have a parent');
        $this->assertEquals($result[6], $result[7]->getParent());

        // Klara Ballouhey extra parsed parent columns contains Rodrigo Scheurer.
        $this->assertEquals('Rodrigo Scheurer', $result->getExtra($result[7], MemberXlsImporter::HEADER_PARENT));

        $this->assertEquals('Jaden_Rousseau17@gmail.com', $result[0]->getEmail());
        $this->assertEquals('+41216157840', $result[1]->getPhone());
    }
}
