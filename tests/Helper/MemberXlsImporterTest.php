<?php

namespace App\Tests\Helper;

use App\Helper\AddressConverterService;
use App\Helper\MemberXlsImporter;
use PHPUnit\Framework\TestCase;
use Symfony\Component\ErrorHandler\BufferingLogger;

class MemberXlsImporterTest extends TestCase
{
    public function testImport()
    {
        $logger = new BufferingLogger();
        $importer = new MemberXlsImporter(new AddressConverterService(), $logger);

        $result = $importer->parse(__DIR__.'/../../src/DataFixtures/members_fixtures.xlsx');

        // 23 user are parsed
        $this->assertCount(23, $result);

        // Yannick Humbert-Droz's parent is Jara Schnider
        $this->assertEquals($result[2]->getParent(), $result[1]);

        // Klara Ballouhey's parent is Rodrigo Scheurer
        $this->assertEquals($result[7]->getParent(), $result[6]);

        $this->assertEquals('Jaden_Rousseau17@gmail.com', $result[0]->getEmail());
        $this->assertEquals('+41216157840', $result[1]->getPhone());
    }
}
