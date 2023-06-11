<?php

namespace App\Bill;

use App\Repository\InvoiceRepository;
use Genkgo\Camt\DTO\Message;
use Genkgo\Camt\DTO\RemittanceInformation;
use kmukku\phpIso11649\phpIso11649;
use Symfony\Component\Validator\ConstraintViolation;
use Symfony\Component\Validator\ConstraintViolationList;

class CamtProcessor
{
    private string $iban;
    private InvoiceRepository $invoiceRepository;
    private string $customerIdentificationNumber;

    public function __construct(string $iban, string $customerIdentificationNumber, InvoiceRepository $invoiceRepository)
    {
        $this->iban = str_replace(' ', '', $iban);
        $this->invoiceRepository = $invoiceRepository;
        $this->customerIdentificationNumber = $customerIdentificationNumber;
    }

    public function parse(Message $message): CamtResultList
    {
        $errors = new ConstraintViolationList();
        $results = [];
        foreach ($message->getRecords() as $messageNum => $record) {
            $id = $record->getAccount()->getIdentification();
            if ($id !== $this->iban) {
                $errors->add(new ConstraintViolation('IBAN mismatch', null, [], null, 'account', $id, null, null, null, $record));
                continue;
            }
            foreach ($record->getEntries() as $entryNum => $entry) {
                $path = sprintf('[%s][%s]', $messageNum, $entryNum);

                $amount = $entry->getAmount()->getAmount();
                if ($amount < 0) {
                    $errors->add(new ConstraintViolation('Negative amount', null, [], null, $path.'amount', $amount, null, null, null, $entry));
                    continue;
                }
                if ('CHF' !== $entry->getAmount()->getCurrency()->getCode()) {
                    $errors->add(new ConstraintViolation('Currency should be CHF', null, [], null, $path.'amount', $amount, null, null, null, $entry));
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

                $results[] = new CamtResultItem(
                    $amount,
                    $entry,
                    $infos->getStructuredBlock()?->getAdditionalRemittanceInformation(),
                    $infos->getStructuredBlock()?->getCreditorReferenceInformation()?->getRef(),
                );
            }
        }
        $result = new CamtResultList($errors, $results);
        $this->fillInvoices($result);

        return $result;
    }

    private function fillInvoices(CamtResultList $results)
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
}
