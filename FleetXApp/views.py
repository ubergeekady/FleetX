from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.db.models import Q
from django.views.generic import TemplateView, DetailView, View, ListView, FormView
from django.apps import apps
from django.http import Http404
from . import models
from . import forms
from . import utils
import os
import json
import uuid
import datetime

class RegisterView(FormView):
	template_name = "userarea/register.html"
	form_class = forms.RegisterForm

	def get(self, request):
		if request.user.is_authenticated:
			return HttpResponseRedirect(reverse('fleetxapp:dashboard'))

		form = self.form_class(initial=self.initial)
		return render(request, self.template_name, {'form': form})

	def post(self, request, *args, **kwargs):
		form = self.form_class(request.POST)
		if form.is_valid():
			uid = uuid.uuid4().hex[:20]
			a = models.Signups(uuid=uid, organization_name=form.cleaned_data['organization_name'],
				full_name=form.cleaned_data['full_name'], email=form.cleaned_data['email'],
				password=form.cleaned_data['password'])
			a.save()
			link = "http://"+django_settings.HOME_URL+"/emailconfirm/" + uid + "/"
			template = get_template('emails/email_signup.html')
			html_content = template.render({"confirmlink":link})
			subject = "Please validate your email address."
			utils.send_email(subject,"aditya@espertosys.com",html_content)

			form = self.form_class(initial=self.initial)
			return render(request, self.template_name, {'form': form , 'form_success':True})
		return render(request, self.template_name, {'form': form})



class EmailConfirmView(View):
	def get(self, request, uid):
		signupobj= get_object_or_404(models.Signups, uuid=uid)
		User.objects.create_user(signupobj.email, signupobj.email, signupobj.password)
		user = authenticate(username=signupobj.email, password=signupobj.password)
		ac = models.Account.objects.create(owner = user, timezone="GMT", organization_name=signupobj.organization_name)
		models.Contact.objects.create(user=user, account=ac, full_name=signupobj.full_name)
		login(request,user)
		signupobj.delete()
		return HttpResponseRedirect(reverse('fleetxapp:dashboard'))



class ForgotPasswordView(FormView):
	template_name = "userarea/forgotpassword.html"
	form_class = forms.ForgotPasswordForm

	def get(self, request):
		if request.user.is_authenticated:
			return HttpResponseRedirect(reverse('fleetxapp:dashboard'))

		form = self.form_class(initial=self.initial)
		return render(request, self.template_name, {'form': form})

	def post(self, request, *args, **kwargs):
		form = self.form_class(request.POST)
		if form.is_valid():
			uid = uuid.uuid4().hex[:20]
			u = User.objects.get(email = form.cleaned_data["email"])
			u.set_password(uid)
			u.save()
			template = get_template('emails/email_forgotpassword.html')
			html_content = template.render({"newpassword":uid})
			subject = "Your new password at FleetX"
			utils.send_email(subject,"aditya@espertosys.com",html_content)
			form = self.form_class(initial=self.initial)
			return render(request, self.template_name, {'form': form , 'form_success':True})
		return render(request, self.template_name, {'form': form})



class LoginView(FormView):
	template_name = "userarea/login.html"
	form_class = forms.LoginForm

	def get(self, request):
		if request.user.is_authenticated:
			return HttpResponseRedirect(reverse('fleetxapp:dashboard'))

		form = self.form_class(initial=self.initial)
		return render(request, self.template_name, {'form': form})

	def post(self, request, *args, **kwargs):
		form = self.form_class(request.POST)
		if form.is_valid():
			user = authenticate(username=form.cleaned_data["email"], password=form.cleaned_data["password"])
			if user==None:
				return render(request, self.template_name, {'form': form , 'other_error':"Incorrect password"})
			else:
				login(request, user)
				return HttpResponseRedirect(reverse('fleetxapp:dashboard'))

		return render(request, self.template_name, {'form': form})



@method_decorator(login_required, name='dispatch')
class LogoutView(View):
	def get(self, request):
		logout(request)
		return HttpResponseRedirect(reverse('fleetxapp:login'))


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class FileUploadView(View):
	def post(self, request, *args, **kwargs):
		print(request.POST)
		models.Files.objects.create(account = request.user.contact.account,
			url=request.POST.get('url',''),
			file_type=request.POST.get('file_type',''),
			linked_object_type=request.POST.get('linked_object_type',''),
			linked_object_id=request.POST.get('linked_object_id',''))
		return HttpResponse("true")


@method_decorator(login_required, name='dispatch')
class CommentAddView(View):
	def get(self, request, object_id, object_type):
		if object_type not in ['Vehicle','Issues','ServiceReminders','VehicleReminders']:
			raise Http404
		mymodel = apps.get_model('FleetXApp', object_type)
		myobject = get_object_or_404(mymodel, pk=object_id)
		form = forms.CommentForm()
		return render(request, "userarea/add_comment.html", {'form':form, 'page_title':'Add Comment To '+object_type+' #'+str(object_id) })
	def post(self, request, object_id, object_type, *args, **kwargs):
		if object_type not in ['Vehicle','Issues','ServiceReminders','VehicleReminders']:
			raise Http404
		mymodel = apps.get_model('FleetXApp', object_type)
		myobject = get_object_or_404(mymodel, pk=object_id)		
		form = forms.CommentForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.author = self.request.user.contact
			instance.linked_object_type = object_type
			instance.linked_object_id = object_id
			instance.save()
			return HttpResponseRedirect(request.GET.get('next'))
		return render(request, "userarea/add_comment.html", {'form':form, 'page_title':'Add Comment To '+object_type+' #'+str(object_id) })


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
	template_name = "userarea/dashboard.html"



@method_decorator(login_required, name='dispatch')
class VehicleListView(ListView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_list.html"
	def get_queryset(self):
		queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		return queryset



@method_decorator(login_required, name='dispatch')
class VehicleDetailView(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_detail.html"
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['vehicledetails']=True
		return context


@method_decorator(login_required, name='dispatch')
class VehicleEditView(View):
	def get(self, request, pk):
		object = get_object_or_404(models.Vehicle, pk=pk)
		form = forms.VehicleForm(instance=object)
		form.fields['vehicle_type'].queryset = models.MasterVehicleTypes.objects.filter(account=self.request.user.contact.account)
		form.fields['status'].queryset = models.MasterVehicleStatus.objects.filter(account=self.request.user.contact.account)
		form.fields['make'].queryset = models.MasterMakes.objects.filter(account=self.request.user.contact.account)
		form.fields['model'].queryset = models.MasterModels.objects.filter(account=self.request.user.contact.account)
		form.fields['assigned_to'].queryset = models.Contact.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/vehicles/vehicle_edit.html", {'object': object, 'form':form, 'page_title':'Edit Vehicle' , 'vehicledetails':True})
	def post(self, request, pk, *args, **kwargs):
		object = get_object_or_404(models.Vehicle, pk=pk)	
		form = forms.VehicleForm(request.POST, instance=object)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('fleetxapp:vehicledetail',args=[pk]))
		return render(request, "userarea/vehicles/vehicle_edit.html", {'object': object, 'form':form, 'page_title':'Edit Vehicle' , 'vehicledetails':True})



@method_decorator(login_required, name='dispatch')
class VehicleAddView(View):
	def get(self, request):
		form = forms.VehicleForm()
		form.fields['vehicle_type'].queryset = models.MasterVehicleTypes.objects.filter(account=self.request.user.contact.account)
		form.fields['status'].queryset = models.MasterVehicleStatus.objects.filter(account=self.request.user.contact.account)
		form.fields['make'].queryset = models.MasterMakes.objects.filter(account=self.request.user.contact.account)
		form.fields['model'].queryset = models.MasterModels.objects.filter(account=self.request.user.contact.account)
		form.fields['assigned_to'].queryset = models.Contact.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/vehicles/vehicle_new.html", {'object': object, 'form':form, 'page_title':'Add Vehicle'})
	def post(self, request, *args, **kwargs):
		form = forms.VehicleForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			return HttpResponseRedirect(reverse('fleetxapp:vehicledetail',args=[instance.pk]))
		return render(request, "userarea/vehicles/vehicle_new.html", {'object': object, 'form':form, 'page_title':'Edit Vehicle'})


@method_decorator(login_required, name='dispatch')
class VehiclePhotosView(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_photos.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['photos'] = models.Files.objects.filter(account=self.request.user.contact.account,
				file_type = 'IMAGE',
				linked_object_type = 'VEHICLE',
				linked_object_id=self.kwargs['pk']
			)
		context['vehiclephotos']=True
		return context

@method_decorator(login_required, name='dispatch')
class VehicleDocumentsView(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_documents.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['photos'] = models.Files.objects.filter(account=self.request.user.contact.account,
				file_type = 'DOCUMENT',
				linked_object_type = 'VEHICLE',
				linked_object_id=self.kwargs['pk']
			)
		context['vehicledocuments']=True		
		return context



@method_decorator(login_required, name='dispatch')
class VehicleCommentsView(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_comments.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['comments'] = models.Comments.objects.filter(account=self.request.user.contact.account,
				linked_object_type = 'Vehicle',
				linked_object_id=self.kwargs['pk']
			).order_by('-timestamp')
		context['vehiclecomments']=True		
		return context


@method_decorator(login_required, name='dispatch')
class VehicleAllRemindersView(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_allreminders.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['vehiclereminders'] = models.VehicleReminders.objects.filter(account=self.request.user.contact.account,
				vehicle__id = self.kwargs['pk']
			)
		context['servicereminders'] = models.ServiceReminders.objects.filter(account=self.request.user.contact.account,
				vehicle__id = self.kwargs['pk']
			)

		context['vehiclereminderstab']=True		
		return context



@method_decorator(login_required, name='dispatch')
class VehicleAllIssues(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_allissues.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['vehicleissues'] = models.Issues.objects.filter(account=self.request.user.contact.account,
				vehicle__id = self.kwargs['pk']
			)
		context['vehicleissuestab']=True		
		return context


@method_decorator(login_required, name='dispatch')
class VehicleAllFuelEnties(DetailView):
	model = models.Vehicle
	template_name = "userarea/vehicles/vehicle_allfuelentries.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['vehiclefuelentries'] = models.FuelEntry.objects.filter(account=self.request.user.contact.account,
				vehicle__id = self.kwargs['pk']
			)
		context['vehiclefuelentriestab']=True		
		return context



@method_decorator(login_required, name='dispatch')
class VehicleReminderListView(ListView):
	model = models.VehicleReminders	
	template_name = "userarea/reminders/vehiclereminders.html"
	def get_queryset(self):
		queryset = models.VehicleReminders.objects.filter(account=self.request.user.contact.account)
		return queryset


@method_decorator(login_required, name='dispatch')
class VehicleReminderAddView(View):
	def get(self, request, pk):
		if pk > 0:
			object = get_object_or_404(models.Vehicle, pk=pk)
			form = forms.VehicleReminderForm(initial={'vehicle':object})
		else:
			form = forms.VehicleReminderForm()
		form.fields['vehicle'].queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		form.fields['vehicle_reminder_type'].queryset = models.MasterVehicleReminderTypes.objects.filter(account=self.request.user.contact.account)
		form.fields['notify_contacts'].queryset = models.Contact.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/reminders/vehiclereminder_new.html", {'form':form, 'page_title':'Add Vehicle Reminder'})
	def post(self, request, *args, **kwargs):
		form = forms.VehicleReminderForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:vehiclereminders'))
		return render(request, "userarea/reminders/vehiclereminder_new.html", {'form':form, 'page_title':'Add Vehicle Reminder'})



@method_decorator(login_required, name='dispatch')
class VehicleReminderEditView(View):
	def get(self, request, pk):
		object = get_object_or_404(models.VehicleReminders, pk=pk)
		form = forms.VehicleReminderForm(instance=object)
		form.fields['vehicle'].queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		form.fields['vehicle_reminder_type'].queryset = models.MasterVehicleReminderTypes.objects.filter(account=self.request.user.contact.account)
		form.fields['notify_contacts'].queryset = models.Contact.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/reminders/vehiclereminder_new.html", {'form':form, 'page_title':'Edit Vehicle Reminder'})
	def post(self, request, pk, *args, **kwargs):
		object = get_object_or_404(models.VehicleReminders, pk=pk)
		form = forms.VehicleReminderForm(request.POST, instance=object)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:vehiclereminders'))
		return render(request, "userarea/reminders/vehiclereminder_new.html", {'form':form, 'page_title':'Edit Vehicle Reminder'})


@method_decorator(login_required, name='dispatch')
class ServiceReminderListView(ListView):
	model = models.ServiceReminders	
	template_name = "userarea/reminders/servicereminders.html"
	def get_queryset(self):
		queryset = models.ServiceReminders.objects.filter(account=self.request.user.contact.account)
		return queryset


@method_decorator(login_required, name='dispatch')
class ServiceReminderAddView(View):
	def get(self, request, pk):
		if pk > 0:
			object = get_object_or_404(models.Vehicle, pk=pk)
			form = forms.ServiceReminderForm(initial={'vehicle':object})
		else:
			form = forms.ServiceReminderForm()
		form.fields['vehicle'].queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		form.fields['service_reminder_type'].queryset = models.MasterServiceReminderTypes.objects.filter(account=self.request.user.contact.account)
		form.fields['notify_contacts'].queryset = models.Contact.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/reminders/servicereminder_new.html", {'form':form, 'page_title':'Add Service Reminder'})
	def post(self, request, *args, **kwargs):
		form = forms.ServiceReminderForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:servicereminders'))
		return render(request, "userarea/reminders/servicereminder_new.html", {'form':form, 'page_title':'Add Service Reminder'})



@method_decorator(login_required, name='dispatch')
class ServiceReminderEditView(View):
	def get(self, request, pk):
		object = get_object_or_404(models.ServiceReminders, pk=pk)
		form = forms.ServiceReminderForm(instance=object)
		form.fields['vehicle'].queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		form.fields['service_reminder_type'].queryset = models.MasterServiceReminderTypes.objects.filter(account=self.request.user.contact.account)
		form.fields['notify_contacts'].queryset = models.Contact.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/reminders/servicereminder_new.html", {'form':form, 'page_title':'Edit Service Reminder'})
	def post(self, request, pk, *args, **kwargs):
		object = get_object_or_404(models.ServiceReminders, pk=pk)
		form = forms.ServiceReminderForm(request.POST, instance=object)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:servicereminders'))
		return render(request, "userarea/reminders/servicereminder_new.html", {'form':form, 'page_title':'Edit Service Reminder'})



@method_decorator(login_required, name='dispatch')
class IssuesListView(ListView):
	model = models.Issues	
	template_name = "userarea/issues/issues.html"
	def get_queryset(self):
		queryset = models.Issues.objects.filter(account=self.request.user.contact.account)
		return queryset


@method_decorator(login_required, name='dispatch')
class IssueAddView(View):
	def get(self, request, pk):
		if pk > 0:
			object = get_object_or_404(models.Vehicle, pk=pk)
			form = forms.IssueForm(initial={'vehicle':object})
		else:
			form = forms.IssueForm()
		form.fields['vehicle'].queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/issues/issue_new.html", {'form':form, 'page_title':'Add Issue'})
	def post(self, request, *args, **kwargs):
		form = forms.IssueForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:issues'))
		return render(request, "userarea/issues/issue_new.html", {'form':form, 'page_title':'Add Issue'})



@method_decorator(login_required, name='dispatch')
class IssueEditView(View):
	def get(self, request, pk):
		object = get_object_or_404(models.Issues, pk=pk)
		form = forms.IssueForm(instance=object)
		form.fields['vehicle'].queryset = models.Vehicle.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/issues/issue_new.html", {'form':form, 'page_title':'Edit Issue'})
	def post(self, request, pk, *args, **kwargs):
		object = get_object_or_404(models.Issues, pk=pk)
		form = forms.IssueForm(request.POST, instance=object)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:issues'))
		return render(request, "userarea/issues/issue_new.html", {'form':form, 'page_title':'Edit Issue'})



@method_decorator(login_required, name='dispatch')
class VendorsListView(ListView):
	model = models.Vendors	
	template_name = "userarea/vendors/vendors.html"
	def get_queryset(self):
		queryset = models.Vendors.objects.filter(account=self.request.user.contact.account)
		return queryset


@method_decorator(login_required, name='dispatch')
class VendorsAddView(View):
	def get(self, request):
		form = forms.VendorsForm()
		form.fields['vendor_type'].queryset = models.MasterVendorTypes.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/vendors/vendors_new.html", {'form':form, 'page_title':'Add Vendor'})
	def post(self, request, *args, **kwargs):
		form = forms.VendorsForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:vendors'))
		return render(request, "userarea/issues/issue_new.html", {'form':form, 'page_title':'Add Vendor'})



@method_decorator(login_required, name='dispatch')
class VendorsEditView(View):
	def get(self, request, pk):
		object = get_object_or_404(models.Vendors, pk=pk)
		form = forms.VendorsForm(instance=object)
		form.fields['vendor_type'].queryset = models.MasterVendorTypes.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/vendors/vendors_new.html", {'form':form, 'page_title':'Edit Vendor'})
	def post(self, request, pk, *args, **kwargs):
		object = get_object_or_404(models.Vendors, pk=pk)
		form = forms.VendorsForm(request.POST, instance=object)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:vendors'))
		return render(request, "userarea/vendors/vendors_new.html", {'form':form, 'page_title':'Edit Vendor'})


@method_decorator(login_required, name='dispatch')
class FuelEntryListView(ListView):
	model = models.FuelEntry	
	template_name = "userarea/fuelentries/fuelentries.html"
	def get_queryset(self):
		queryset = models.FuelEntry.objects.filter(account=self.request.user.contact.account)
		return queryset


@method_decorator(login_required, name='dispatch')
class FuelEntryAddView(View):
	def get(self, request,pk):
		if pk > 0:
			object = get_object_or_404(models.FuelEntry, pk=pk)
			form = forms.FuelEntryForm(initial={'vehicle':object})
		else:
			form = forms.FuelEntryForm()
		form.fields['vendor'].queryset = models.Vendors.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/fuelentries/fuelentries_new.html", {'form':form, 'page_title':'Add Fuel Entry'})
	def post(self, request, *args, **kwargs):
		form = forms.FuelEntryForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:fuelentries'))
		return render(request, "userarea/fuelentries/fuelentries_new.html", {'form':form, 'page_title':'Add Fuel Entry'})



@method_decorator(login_required, name='dispatch')
class FuelEntryEditView(View):
	def get(self, request, pk):
		object = get_object_or_404(models.FuelEntry, pk=pk)
		form = forms.FuelEntryForm(instance=object)
		form.fields['vendor'].queryset = models.Vendors.objects.filter(account=self.request.user.contact.account)
		return render(request, "userarea/fuelentries/fuelentries_new.html", {'form':form, 'page_title':'Edit Fuel Entry'})
	def post(self, request, pk, *args, **kwargs):
		object = get_object_or_404(models.FuelEntry, pk=pk)
		form = forms.FuelEntryForm(request.POST, instance=object)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.account = self.request.user.contact.account
			instance.save()
			form.save_m2m()
			#Crazy - http://www.joshuakehn.com/2013/6/23/django-m2m-modelform.html
			return HttpResponseRedirect(reverse('fleetxapp:fuelentries'))
		return render(request, "userarea/fuelentries/fuelentries_new.html", {'form':form, 'page_title':'Edit Fuel Entry'})




@method_decorator(login_required, name='dispatch')
class FuelListView(TemplateView):
	template_name = "userarea/fuel.html"

@method_decorator(login_required, name='dispatch')
class ReportListView(TemplateView):
	template_name = "userarea/reports.html"

@method_decorator(login_required, name='dispatch')
class ContactListView(TemplateView):
	template_name = "userarea/contacts.html"

@method_decorator(login_required, name='dispatch')
class SettingsView(TemplateView):
	template_name = "userarea/settings.html"

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
	template_name = "userarea/profile.html"