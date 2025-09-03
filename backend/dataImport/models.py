# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Categorias(models.Model):
    nombre = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'categorias'


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Escuelas(models.Model):
    nombre = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'escuelas'


class InventarioItems(models.Model):
    inventario = models.CharField(unique=True, max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    marca = models.CharField(max_length=120, blank=True, null=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_recibido = models.DateField()
    categoria = models.ForeignKey(Categorias, models.DO_NOTHING, blank=True, null=True)
    ubicacion = models.ForeignKey('Ubicaciones', models.DO_NOTHING, blank=True, null=True)
    entregado_por = models.ForeignKey('Usuarios', models.DO_NOTHING, blank=True, null=True)
    recibido_por = models.ForeignKey('Usuarios', models.DO_NOTHING, related_name='inventarioitems_recibido_por_set', blank=True, null=True)
    escuela = models.ForeignKey(Escuelas, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventario_items'


class InventarioTrazabilidad(models.Model):
    id = models.BigAutoField(primary_key=True)
    inventario = models.ForeignKey(InventarioItems, models.DO_NOTHING, db_column='inventario')
    fecha = models.DateTimeField()
    accion = models.TextField()
    detalle = models.TextField(blank=True, null=True)
    usuario_id = models.IntegerField(blank=True, null=True)
    meta = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventario_trazabilidad'


class Ubicaciones(models.Model):
    edificio = models.CharField(max_length=120)
    salon = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = 'ubicaciones'
        unique_together = (('edificio', 'salon'),)


class Usuarios(models.Model):
    codigo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=150)
    email = models.CharField(unique=True, max_length=150)
    password_hash = models.TextField()
    rol = models.TextField()  # This field type is a guess.
    escuela = models.ForeignKey(Escuelas, models.DO_NOTHING, blank=True, null=True)
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'usuarios'
