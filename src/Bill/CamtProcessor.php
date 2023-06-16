<?php

namespace App\Bill;

use App\Repository\InvoiceRepository;
use Genkgo\Camt\DTO\Entry;
use Genkgo\Camt\DTO\Message;
use Genkgo\Camt\DTO\RemittanceInformation;
use kmukku\phpIso11649\phpIso11649;
use Symfony\Component\Validator\ConstraintViolation;
use Symfony\Component\Validator\ConstraintViolationList;

class CamtProcessor
{
    private string $iban;
    private InvoiceRepository $invoiceRepository;

    public function __construct(string $iban, InvoiceRepository $invoiceRepository)
    {
        $this->iban = str_replace(' ', '', $iban);
        $this->invoiceRepository = $invoiceRepository;
    }

    public function parse(Message $message): CamtResultList
    {
        $errors = new ConstraintViolationList();
        $results = [];
        foreach ($message->getRecords() as $messageNum => $record) {
            $id = $record->getAccount()->getIdentification();
            if ($id !== $this->iban) {
                $errors->add(new ConstraintViolation('IBAN mismatch', null, ['iban' => $id], null, 'account', $id, null, null, null, $record));
                continue;
            }
            foreach ($record->getEntries() as $entryNum => $entry) {
                $path = sprintf('[%s][%s]', $messageNum, $entryNum);

                $amount = $entry->getAmount()->getAmount();
                if ($amount < 0) {
                    // $errors->add(new ConstraintViolation('Negative amount', null, ['amount' => $amount], null, $path.'amount', $amount, null, null, null, $entry));
                    continue;
                }
                if ('CHF' !== $entry->getAmount()->getCurrency()->getCode()) {
                    $errors->add(new ConstraintViolation('Currency should be CHF', null, ['currency' => $entry->getAmount()->getCurrency()->getCode()], null, $path.'amount', $amount, null, null, null, $entry));
                    continue;
                }

                /** @var RemittanceInformation|null $infos */
                $infos = $entry->getTransactionDetail()?->getRemittanceInformation();

                if (null === $infos) {
                    $errors->add(new ConstraintViolation('No remitance information', null, [], null, $path.'transactionDetails', $amount, null, null, null, $entry));
                    continue;
                }

                if ('SCOR' !== $infos->getStructuredBlock()?->getCreditorReferenceInformation()?->getCode()) {
                    $errors->add(new ConstraintViolation('No SCOR reference', null, [], null, $path.'CreditorReferenceInformation', $amount, null, null, null, $entry));
                    continue;
                }

                $results[] = $this->createResultItemFromEntry($entry);
            }
        }

        $recoveredResults = $this->convertErrorToTransactionBasedOnInvoiceTransactionId($errors);

        $result = new CamtResultList($errors, array_merge($results, $recoveredResults));
        $this->fillInvoices($result);

        return $result;
    }

    private function fillInvoices(CamtResultList $results): void
    {
        $refs = [];
        $map = [];
        $iso = new phpIso11649();

        foreach ($results->getResults() as $result) {
            if (false === $iso->validateRfReference($result->ref)) {
                continue;
            }
            $ref = (int) substr($result->ref, 4);
            $map[$result->ref] = $ref;
            $refs[] = $ref;
        }
        $invoices = $this->invoiceRepository->findByReferences($refs);
        foreach ($results->getResults() as $result) {
            $refId = $map[$result->ref] ?? null;

            if (null !== $refId && array_key_exists($refId, $invoices)) {
                $result->setInvoice($invoices[$refId]);
                unset($invoices[$refId]);
                unset($map[$result->ref]);
            }
        }
    }

    private function getContact(Entry $entry): ?string
    {
        return ($entry->getTransactionDetail()?->getRelatedParties()[1])?->getRelatedPartyType()?->getName() ?? null;
    }

    private function getTransactionId(Entry $entry): ?string
    {
        return $entry->getTransactionDetail()?->getReference()?->getTransactionId() ?? null;
    }

    /**
     * @return array<CamtResultItem>
     */
    private function convertErrorToTransactionBasedOnInvoiceTransactionId(ConstraintViolationList $errors): array
    {
        $transactionIds = [];
        $result = [];
        foreach ($errors as $error) {
            if (false === $error->getCause() instanceof Entry) {
                continue;
            }
            $transactionIds[] = $this->getTransactionId($error->getCause());
        }
        // Remove null transaction ids
        $transactionIds = array_filter($transactionIds);

        $invoices = $this->invoiceRepository->findByTransactionIds($transactionIds);

        foreach ($errors as $key => $error) {
            if (false === $error->getCause() instanceof Entry) {
                continue;
            }
            $transactionId = $this->getTransactionId($error->getCause());
            if (null === $transactionId || false === array_key_exists($transactionId, $invoices)) {
                continue;
            }

            // The error is now handled
            $errors->remove($key);

            $result[] = $this->createResultItemFromEntry($error->getCause())->setInvoice($invoices[$transactionId]);
        }

        return $result;
    }

    private function createResultItemFromEntry(Entry $entry): CamtResultItem
    {
        /** @var RemittanceInformation|null $infos */
        $infos = $entry->getTransactionDetail()?->getRemittanceInformation();

        $message = $infos?->getStructuredBlock()?->getAdditionalRemittanceInformation();
        if (null === $message) {
            $message = $infos?->getUnstructuredBlock()?->getMessage();
        }
        if (null === $message) {
            $message = $entry->getAdditionalInfo();
        }
        $ref = $infos?->getStructuredBlock()?->getCreditorReferenceInformation()?->getRef();

        return new CamtResultItem(
            (int) $entry->getAmount()->getAmount(),
            $entry,
            $message,
            $ref,
            $this->getContact($entry),
            $this->getTransactionId($entry),
        );
    }
}
