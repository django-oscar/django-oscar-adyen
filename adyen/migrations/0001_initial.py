# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AdyenTransaction'
        db.create_table('adyen_adyentransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order_number', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=255)),
            ('reference', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(null=True, blank=True, decimal_places=2, max_digits=12)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3, default='EUR')),
            ('ip_address', self.gf('django.db.models.fields.GenericIPAddressField')(null=True, max_length=39, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('adyen', ['AdyenTransaction'])


    def backwards(self, orm):
        # Deleting model 'AdyenTransaction'
        db.delete_table('adyen_adyentransaction')


    models = {
        'adyen.adyentransaction': {
            'Meta': {'object_name': 'AdyenTransaction', 'ordering': "('-date_created',)"},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'blank': 'True', 'decimal_places': '2', 'max_digits': '12'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'default': "'EUR'"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.GenericIPAddressField', [], {'null': 'True', 'max_length': '39', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'order_number': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255'}),
            'reference': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        }
    }

    complete_apps = ['adyen']