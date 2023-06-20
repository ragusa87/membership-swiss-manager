<?php

namespace App\Tests\Bill;

use App\Bill\CamtProcessor;
use Genkgo\Camt\Config;
use Genkgo\Camt\DTO\Message;
use Genkgo\Camt\Reader;
use kmukku\phpIso11649\phpIso11649;
use Symfony\Bundle\FrameworkBundle\Test\KernelTestCase;

class CamtProcessorTest extends KernelTestCase
{
    public function testCurrencyCheck(): void
    {
        /** @var CamtProcessor $camtProcessor */
        $camtProcessor = self::getContainer()->get(CamtProcessor::class);

        $result = $camtProcessor->parse($this->getMockCamt('2013-12-27_C53_DE14740618130000033626_EUR_A000IH.xml'));
        $this->assertEmpty($result->getResults());
        $this->assertCount(1, $result->getErrors());
        $this->assertEquals('Currency should be CHF', $result->getErrors()[0]->getMessage());
    }

    public function testReferenceNeeded(): void
    {
        /** @var CamtProcessor $camtProcessor */
        $camtProcessor = self::getContainer()->get(CamtProcessor::class);

        $result = $camtProcessor->parse($this->getMockCamt('2013-12-27_C53_DE14740618130000033626_CHF_A000IH.xml'));
        $this->assertEmpty($result->getResults());
        $this->assertCount(1, $result->getErrors());
        $this->assertEquals('No SCOR reference', $result->getErrors()[0]->getMessage());
    }

    public function testIbanMatch(): void
    {
        /** @var CamtProcessor $camtProcessor */
        $camtProcessor = self::getContainer()->get(CamtProcessor::class);

        $result = $camtProcessor->parse($this->getMockCamt('2013-12-27_C53_DE14740618130000033626_CHFINVALIDIBAN_A000IH.xml'));
        $this->assertEmpty($result->getResults());
        $this->assertCount(4, $result->getErrors());
        foreach ($result->getErrors()->getIterator() as $error) {
            $this->assertEquals('IBAN mismatch', $error->getMessage());
        }
    }

    public function testResultsRefs(): void
    {
        /** @var CamtProcessor $camtProcessor */
        $camtProcessor = self::getContainer()->get(CamtProcessor::class);

        $result = $camtProcessor->parse($this->getMockCamt('2013-12-27_C53_DE14740618130000033626_CHFOK_A000IH.xml'));
        $this->assertCount(0, $result->getErrors());
        $this->assertNotEmpty($result->getResults());

        foreach ($result->getResults() as $i => $entry) {
            $expectedRef = $i + 8;
            $expectedRefString = $this->generateRefString($expectedRef);
            $this->assertSame($expectedRefString, $entry->ref, 'Ref is invalid');
            $this->assertSame($expectedRefString, $entry->getReferenceString(), 'Invalid reference string');
            $this->assertNull($entry->getInvoice(), 'invoice should not have matches');
            $this->assertNotNull($entry->message, 'should have a message');
            $this->assertSame($expectedRef, $entry->getReferenceInt(), 'reference conversion invalid for index '.$i);
        }
    }

    protected function generateRefString(int $num): string
    {
        return (new phpIso11649())->generateRfReference(str_pad((string) $num, 21, '0', STR_PAD_LEFT), false);
    }

    public function testSimpleInvoiceMatch(): void
    {
        /** @var CamtProcessor $camtProcessor */
        $camtProcessor = self::getContainer()->get(CamtProcessor::class);

        $message = $this->getMockCamtAndAlterIt('2013-12-27_C53_DE14740618130000033626_CHFOK_A000IH.xml', function (string $content) {
            return str_replace($this->generateRefString(8), $this->generateRefString(1), $content);
        });
        $result = $camtProcessor->parse($message);
        $this->assertCount(0, $result->getErrors());
        $this->assertNotEmpty($result->getResults());
        $this->assertNotNull($result->getResults()[0]->getInvoice());
    }

    protected function getMockCamtAndAlterIt(string $filename, callable $alterFile): Message
    {
        $reader = new Reader(Config::getDefault());

        $content = file_get_contents(__DIR__.'/../assets/'.$filename);
        if (false === $content) {
            throw new \RuntimeException('Mock not found '.$filename);
        }

        $content = $alterFile($content);
        if (null === $content) {
            throw new \RuntimeException('Mock callable should return a value');
        }

        return $reader->readString($content);
    }

    protected function getMockCamt(string $filename): Message
    {
        $reader = new Reader(Config::getDefault());

        return $reader->readFile(__DIR__.'/../assets/'.$filename);
    }
}
