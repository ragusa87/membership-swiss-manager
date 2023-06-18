<?php

namespace App\Bill;

use _PHPStan_a2a733b6a\React\Http\Io\Transaction;
use App\Repository\InvoiceRepository;
use Genkgo\Camt\DTO\Entry;
use Genkgo\Camt\DTO\EntryTransactionDetail;
use Genkgo\Camt\DTO\Message;
use Genkgo\Camt\DTO\RemittanceInformation;
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

        foreach ($message->getEntries() as $entryNum => $entry) {
            $id = $entry->getRecord()->getAccount()->getIdentification();
            if ($id !== $this->iban) {
                $errors->add(new ConstraintViolation('IBAN mismatch', null, ['iban' => $id], null, 'account', $id, null, null, null, $entry));
                continue;
            }

            $path = sprintf('[%s]', $entryNum);

            $amount = $entry->getAmount()->getAmount();
            if ($amount < 0) {
                // $errors->add(new ConstraintViolation('Negative amount', null, ['amount' => $amount], null, $path.'amount', $amount, null, null, null, $entry));
                continue;
            }
            if ('CHF' !== $entry->getAmount()->getCurrency()->getCode()) {
                $errors->add(new ConstraintViolation('Currency should be CHF', null, ['currency' => $entry->getAmount()->getCurrency()->getCode()], null, $path.'amount', $amount, null, null, null, $entry));
                continue;
            }

            foreach ($entry->getTransactionDetails() as $transactionDetail) {
                /** @var RemittanceInformation|null $infos */
                $infos = $transactionDetail->getRemittanceInformation();

                if (null === $infos) {
                    $errors->add(new ConstraintViolation('No remitance information', null, [], $transactionDetail, $path.'transactionDetails', $amount, null, null, null, $entry));
                    continue;
                }

                if ('SCOR' !== $infos->getStructuredBlock()?->getCreditorReferenceInformation()?->getCode()) {
                    $errors->add(new ConstraintViolation('No SCOR reference', null, [], $transactionDetail, $path.'CreditorReferenceInformation', $amount, null, null, null, $entry));
                    continue;
                }

                $results[] = $this->createResultItemFromEntry($entry, $transactionDetail);
            }
        }

        $recoveredResults = $this->convertErrorToTransactionBasedOnInvoiceTransactionId($errors);

        $result = new CamtResultList($errors, array_merge($results, $recoveredResults));
        $this->fillInvoices($result);

        return $result;
    }

    private function fillInvoices(CamtResultList $results): void
    {
        /** @var array<string,int> $references */
        $references = [];
        /** @var array<string> $transactionsIds */
        $transactionsIds = [];

        // Fetch all the references and transactions Ids
        foreach ($results->getResults() as $result) {
            $transactionsIds[] = $result->transactionId;
            $references[$result->getReferenceString()] = $result->getReferenceInt();
        }

        // Fetch and set the invoices by transaction Ids
        $invoicesByTransactionIds = $this->invoiceRepository->findByTransactionIds($transactionsIds);
        foreach ($results->getResults() as $result) {
            if (null !== $result->getInvoice() || null === $result->transactionId) {
                continue;
            }
            if (false === array_key_exists($result->transactionId, $invoicesByTransactionIds)) {
                continue;
            }

            $result->setInvoice($invoicesByTransactionIds[$result->transactionId]);
            unset($invoicesByTransactionIds[$result->transactionId]);
        }
        unset($invoicesByTransactionIds);

        // Fetch and set the invoices by references
        $invoicesByReferences = $this->invoiceRepository->findByReferences($references);
        foreach ($results->getResults() as $result) {
            if (null === $result->ref || null !== $result->getInvoice()) {
                continue;
            }
            $index = $references[$result->ref] ?? null;
            if (null !== $index) {
                $result->setInvoice($invoicesByReferences[$index]);
                unset($invoicesByReferences[$index]);
            }
        }

        foreach ($results->getResults() as $result) {
            if (null === $result->getInvoice()) {
                $a = 1;
            }
        }
    }

    private function getContact(Entry $entry, EntryTransactionDetail $detail): ?string
    {
        $parties = $detail->getRelatedParties();
        if (empty($parties)) {
            return $entry->getAdditionalInfo();
        }

        return $detail->getRelatedParties()[1]->getRelatedPartyType()->getName();
    }

    private function getTransactionId(EntryTransactionDetail $detail): ?string
    {
        return $detail->getReference()?->getTransactionId();
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
            $transactionIds[] = $this->getTransactionId($error->getCause()->getTransactionDetail());
        }
        // Remove null transaction ids
        $transactionIds = array_filter($transactionIds);

        $invoices = $this->invoiceRepository->findByTransactionIds($transactionIds);

        foreach ($errors as $key => $error) {
            if (false === $error->getCause() instanceof Entry) {
                continue;
            }
            $transactionId = $this->getTransactionId($error->getCause()->getTransactionDetail());
            if (null === $transactionId || false === array_key_exists($transactionId, $invoices)) {
                continue;
            }

            // The error is now handled
            $errors->remove($key);

            $entry = $error->getCause();

            foreach ($entry->getTransactionDetails() as $infos) {
                $result[] = $this->createResultItemFromEntry($entry, $infos)->setInvoice($invoices[$transactionId]);
            }
        }

        return $result;
    }

    private function createResultItemFromEntry(Entry $entry, EntryTransactionDetail $transactionDetail): CamtResultItem
    {
        /** @var RemittanceInformation|null $infos */
        $infos = $transactionDetail->getRemittanceInformation();

        $message = $infos?->getStructuredBlock()?->getAdditionalRemittanceInformation();
        if (null === $message) {
            $message = $infos?->getUnstructuredBlock()?->getMessage();
        }
        if (null === $message) {
            $message = $entry->getAdditionalInfo();
        }

        $ref = $infos?->getStructuredBlock()?->getCreditorReferenceInformation()?->getRef();

        // Sometimes, multiple payment are done with the same reference. In this case we force manual matching.
        if (count($entry->getTransactionDetails()) > 1) {
            $message .= ' to much references';
            $ref = null;
        }

        return new CamtResultItem(
            (int) $transactionDetail->getAmount()?->getAmount(),
            $entry,
            $transactionDetail,
            $message,
            $ref,
            $this->getContact($entry, $transactionDetail),
            $this->getTransactionId($transactionDetail),
        );
    }
}
