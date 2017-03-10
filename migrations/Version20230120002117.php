<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20230120002117 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add invoice timestamplable';
    }

    public function up(Schema $schema): void
    {
        // this up() migration is auto-generated, please modify it to your needs
        $this->addSql('ALTER TABLE invoice ADD COLUMN created_at DATETIME NOT NULL');
        $this->addSql('ALTER TABLE invoice ADD COLUMN updated_at DATETIME NOT NULL');
    }

    public function down(Schema $schema): void
    {
        // this down() migration is auto-generated, please modify it to your needs
        $this->addSql('CREATE TEMPORARY TABLE __temp__invoice AS SELECT id, member_subscription_id, reference, status, price FROM invoice');
        $this->addSql('DROP TABLE invoice');
        $this->addSql('CREATE TABLE invoice (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, member_subscription_id INTEGER NOT NULL, reference INTEGER DEFAULT NULL, status VARCHAR(10) DEFAULT \'created\' NOT NULL, price INTEGER DEFAULT NULL, CONSTRAINT FK_90651744C8948833 FOREIGN KEY (member_subscription_id) REFERENCES member_subscription (id) NOT DEFERRABLE INITIALLY IMMEDIATE)');
        $this->addSql('INSERT INTO invoice (id, member_subscription_id, reference, status, price) SELECT id, member_subscription_id, reference, status, price FROM __temp__invoice');
        $this->addSql('DROP TABLE __temp__invoice');
        $this->addSql('CREATE INDEX IDX_90651744C8948833 ON invoice (member_subscription_id)');
    }
}
